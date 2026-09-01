#!/usr/bin/env python3
"""批量处理参访方案图片的增删改操作（通过远程服务器 API）。

工作流程：
1. 准备好图片文件到 data/images/ 目录
2. 在 data/ 目录下创建 ops.json 配置文件
3. 运行脚本自动执行所有操作

data/ops.json 示例：
{
  "operations": [
    {
      "operation": "create",
      "image_path": "images/01广东/广东-深圳/华为松山湖.png",
      "image_name": "华为松山湖.png",
      "category": "01广东"
    },
    {
      "operation": "update",
      "image_path": "images/09河南/胖东来更新.png",
      "image_name": "胖东来.png",
      "category": "09河南",
      "media_id": "原有的media_id"
    },
    {
      "operation": "delete",
      "media_id": "要删除的media_id"
    }
  ]
}

用法：
    cd /path/to/CS-Agent
    python scripts/image_ops/batch_image_operations.py

    或指定配置文件路径：
    python scripts/image_ops/batch_image_operations.py --config /path/to/ops.json
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import logging
import sys
from pathlib import Path

import httpx
from PIL import Image

SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".bmp"}
MAX_IMAGE_SIZE = 200 * 1024
REMOTE_API_KEY = "cRgCWNHkfrZt7GE47JQtyE9RDY2Pxo4lAs9DQjuSXUY="
REMOTE_API_URL = "https://43.129.183.181/api/visit-image"
REMOTE_ASSETS_URL = "https://43.129.183.181/api/assets/image"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).resolve().parent
OPS_FILE = SCRIPT_DIR / "data" / "ops.json"

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        logger.error("配置文件不存在: %s", config_path)
        sys.exit(1)
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error("配置文件 JSON 格式错误: %s", e)
        sys.exit(1)


def compress_image_to_base64(image_path: Path) -> tuple[str, int] | None:
    try:
        img = Image.open(image_path)
        original_size = image_path.stat().st_size

        if original_size <= MAX_IMAGE_SIZE:
            b64_data = base64.b64encode(image_path.read_bytes()).decode("utf-8")
            return b64_data, original_size

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        target_size = MAX_IMAGE_SIZE

        for scale in [1.0, 0.5, 0.25, 0.1]:
            if scale < 1.0:
                current_img = img.resize(
                    (int(img.size[0] * scale), int(img.size[1] * scale)),
                    Image.LANCZOS
                )
            else:
                current_img = img

            for quality in [85, 70, 55, 40, 30]:
                buffer = io.BytesIO()
                current_img.save(buffer, format="JPEG", quality=quality, optimize=True)
                compressed_size = buffer.tell()

                if compressed_size <= target_size:
                    b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
                    return b64_data, compressed_size

        buffer = io.BytesIO()
        img.resize((int(img.size[0] * 0.1), int(img.size[1] * 0.1)), Image.LANCZOS).save(
            buffer, format="JPEG", quality=20, optimize=True
        )
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return b64_data, buffer.tell()
    except Exception as e:
        logger.error("图片压缩失败: %s", e)
        return None


def read_image_as_base64(image_path: Path) -> str | None:
    if not image_path.exists():
        logger.error("图片文件不存在: %s", image_path)
        return None
    suffix = image_path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        logger.error("不支持的图片格式: %s，仅支持: %s", suffix, ", ".join(SUPPORTED_SUFFIXES))
        return None
    result = compress_image_to_base64(image_path)
    if result:
        b64_data, compressed_size = result
        logger.info("  原始: %.2fMB -> 压缩后: %.2fKB",
                   image_path.stat().st_size / 1024 / 1024, compressed_size / 1024)
    return result[0] if result else None


def validate_operation(op: dict, index: int) -> str | None:
    valid_ops = {"create", "update", "delete"}
    operation = op.get("operation", "")
    if operation not in valid_ops:
        return f"操作 {index + 1}: 无效的 operation '{operation}'，必须是 {valid_ops}"

    if operation == "delete":
        if not op.get("media_id"):
            return f"操作 {index + 1}: delete 操作缺少 media_id"
        return None

    if operation in {"create", "update"}:
        if not op.get("image_name"):
            return f"操作 {index + 1}: {operation} 操作缺少 image_name"
        if not op.get("category"):
            return f"操作 {index + 1}: {operation} 操作缺少 category"
        if operation == "update" and not op.get("media_id"):
            return f"操作 {index + 1}: update 操作缺少 media_id"
        if not op.get("image_path"):
            return f"操作 {index + 1}: {operation} 操作缺少 image_path"
    return None


def resolve_image_path(relative_path: str) -> Path:
    data_dir = SCRIPT_DIR / "data"
    if relative_path.startswith("images/"):
        return data_dir / relative_path
    return data_dir / "images" / relative_path


def _fetch_remote_media_index() -> list[dict]:
    """从服务器拉取 media_index.json。"""
    import paramiko
    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect("43.129.183.181", username="ubuntu", password="Alfie000301")
    sftp = cli.open_sftp()
    try:
        with sftp.open("/data/media_index.json", "r") as f:
            data = json.loads(f.read().decode("utf-8"))
    finally:
        sftp.close()
        cli.close()
    return data

def _scan_local_images(images_dir: Path) -> list[dict]:
    """扫描本地 images/ 目录。

    规则：子目录名 = category (例 images/11山东/foo.png -> category="11山东")
    顶层散放的图会被忽略（无法确定 category，必须由用户告知）。
    """
    if not images_dir.exists():
        return []
    out: list[dict] = []
    for sub in sorted(images_dir.iterdir()):
        if not sub.is_dir():
            continue
        category = sub.name
        for img in sorted(sub.iterdir()):
            if not img.is_file():
                continue
            if img.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            try:
                rel = img.relative_to(SCRIPT_DIR / "data")
            except ValueError:
                rel = img
            out.append({
                "image_path": str(rel.as_posix()),
                "image_name": img.name,
                "category": category,
                "size": img.stat().st_size,
            })
    return out


def _reconcile_plan() -> dict:
    """对账: 扫描 images/ 目录 + 服务器 media_index, 生成 ops.json 草稿。

    保留 ops.json 里现有的 delete 操作（避免 plan 误覆盖用户手编的删除）。
    """
    images_dir = SCRIPT_DIR / "data" / "images"
    local = _scan_local_images(images_dir)

    # 顶层散放图（无 category）警告
    top_level: list[Path] = []
    if images_dir.exists():
        for p in images_dir.iterdir():
            if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES:
                top_level.append(p)
    if top_level:
        logger.warning(
            "发现 %d 张图直接放在 images/ 根目录, 无法推断 category: %s",
            len(top_level),
            ", ".join(p.name for p in top_level),
        )
        logger.warning("必须放到子目录 (例 images/11山东/foo.png), 重新跑 plan")

    logger.info("正在拉取服务器 media_index.json ...")
    remote = _fetch_remote_media_index()
    by_name: dict[tuple[str, str], dict] = {
        (it.get("image_name", ""), it.get("category", "")): it
        for it in remote
    }
    logger.info("服务器: %d 条, 本地扫描: %d 张", len(remote), len(local))

    ops: list[dict] = []
    for item in local:
        key = (item["image_name"], item["category"])
        match = by_name.get(key)
        op: dict = {
            "operation": "update" if match else "create",
            "image_path": item["image_path"],
            "image_name": item["image_name"],
            "category": item["category"],
        }
        if match:
            op["media_id"] = match["media_id"]
            op["_reason"] = "同名同 category, 服务器已存在 -> 覆盖"
        else:
            op["_reason"] = "本地新增 -> 上传到微信"
        ops.append(op)

    # 保留现有 ops.json 里的 delete 操作 (避免 plan 误覆盖)
    existing = OPS_FILE
    if existing.exists():
        try:
            cur = json.loads(existing.read_text())
            for op in cur.get("operations", []):
                if op.get("operation") == "delete":
                    ops.append({
                        **op,
                        "_reason": "从上次 ops.json 保留的 delete 操作",
                    })
        except Exception:
            pass

    # 标出"服务器有但本地无"的图（不自动 delete, 避免误删）
    local_keys = {(i["image_name"], i["category"]) for i in local}
    stale: list[dict] = []
    for (n, c), m in by_name.items():
        if (n, c) not in local_keys:
            stale.append({
                "image_name": n, "category": c, "media_id": m["media_id"],
                "_reason": "服务器有, 本地无 -> 如要删除请手动加 delete 操作",
            })

    return {"operations": ops, "stale_on_server": stale}


def _write_ops(config: dict) -> None:
    OPS_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")


def cmd_plan(_args: argparse.Namespace) -> int:
    config = _reconcile_plan()
    _write_ops(config)

    creates = sum(1 for op in config["operations"] if op["operation"] == "create")
    updates = sum(1 for op in config["operations"] if op["operation"] == "update")
    stale = len(config["stale_on_server"])

    print()
    print("=" * 60)
    print(f"ops.json 草稿已生成: {OPS_FILE}")
    print("=" * 60)
    print(f"  新增 create: {creates}")
    print(f"  更新 update: {updates}")
    print(f"  服务器多余 (不会自动删): {stale}")
    print()
    if creates or updates:
        print("下一步: 检查 ops.json, 确认无误后执行")
        print("  python3 scripts/image_ops/batch_image_operations.py run")
    if stale:
        print()
        print("服务器有但本地无的图 (如要删除, 手动编辑 ops.json 加 delete):")
        for s in config["stale_on_server"][:10]:
            print(f"  - {s['image_name']}  ({s['category']})")
        if len(config["stale_on_server"]) > 10:
            print(f"  ... 还有 {len(config['stale_on_server']) - 10} 条")
    return 0


def cmd_show(_args: argparse.Namespace) -> int:
    if not OPS_FILE.exists():
        print(f"ops.json 不存在: {OPS_FILE}")
        print("先跑 plan: python3 scripts/image_ops/batch_image_operations.py plan")
        return 1
    print(OPS_FILE.read_text())
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config_path = Path(args.config).resolve() if args.config else OPS_FILE
    return main(config_path)


def _upload_local_asset(
    image_path: Path, image_name: str, category: str
) -> bool:
    """同步把图片推到本地资产库 (/api/assets/image) 并 rescan asset_index。

    为什么需要这一步：
    远程 /api/visit-image 只把图片上传到微信素材库并写 /data/media_index.json，
    但 agent 实际查询的是本地 /data/cs-agent-assets/asset_index.json（见
    app/assets/index.py）。如果只调 /api/visit-image 而不同步本地，新图
    对客服 agent 不可见。
    """
    try:
        with open(image_path, "rb") as f:
            files = {"image_file": (image_name, f, "application/octet-stream")}
            data = {"category": category, "image_name": image_name, "api_key": REMOTE_API_KEY}
            with httpx.Client(timeout=60, verify=False) as client:
                resp = client.post(REMOTE_ASSETS_URL, files=files, data=data)
        result = resp.json()
        if result.get("success"):
            logger.info("  ✓ 本地同步: count=%s", result.get("count", ""))
            return True
        logger.error("  ✗ 本地同步失败: %s", result.get("error", "未知错误"))
        return False
    except httpx.HTTPError as e:
        logger.error("  ✗ 本地同步请求失败: %s", e)
        return False
    except Exception:
        logger.exception("  ✗ 本地同步异常")
        return False


def execute_operation(op: dict, index: int, total: int) -> bool:
    operation = op["operation"]
    image_name = op.get("image_name", "")
    category = op.get("category", "")
    media_id = op.get("media_id")
    image_path = op.get("image_path", "")

    logger.info("执行 [%d/%d] %s: %s (%s)",
                index + 1, total, operation.upper(),
                image_name or f"media_id={media_id}", category or "")

    form_data: dict = {"operation": operation, "api_key": REMOTE_API_KEY}

    if operation in {"create", "update"}:
        resolved_path = resolve_image_path(image_path)
        b64_data = read_image_as_base64(resolved_path)
        if not b64_data:
            return False
        form_data["image_name"] = image_name
        form_data["category"] = category
        form_data["base64_data"] = b64_data

    if operation == "update":
        form_data["media_id"] = media_id

    if operation == "delete":
        form_data["media_id"] = media_id

    try:
        with httpx.Client(timeout=60, verify=False) as client:
            response = client.post(REMOTE_API_URL, data=form_data)
        result = response.json()

        if not result.get("success"):
            logger.error("  ✗ 失败: %s", result.get("error", "未知错误"))
            return False

        logger.info("  ✓ 微信素材: media_id=%s", result.get("media_id", ""))

        # create/update 成功后再同步本地资产库（让 agent 能查到这张图）
        if operation in {"create", "update"}:
            return _upload_local_asset(resolved_path, image_name, category)
        return True
    except httpx.HTTPError as e:
        logger.error("  ✗ 请求失败: %s", e)
        return False
    except Exception:
        logger.exception("  ✗ 异常")
        return False


def main(config_path: Path) -> None:
    config = load_config(config_path)
    operations = config.get("operations", [])

    if not operations:
        logger.warning("没有配置任何操作，请检查 %s", config_path)
        return

    for i, op in enumerate(operations):
        error = validate_operation(op, i)
        if error:
            logger.error(error)
            sys.exit(1)

    logger.info("共 %d 个操作，开始执行...", len(operations))
    logger.info("远程服务器: %s", REMOTE_API_URL)

    results: list[bool] = []
    for i, op in enumerate(operations):
        ok = execute_operation(op, i, len(operations))
        results.append(ok)

    success = sum(1 for r in results if r)
    fail = len(results) - success
    logger.info("完成：成功 %d，失败 %d", success, fail)

    if fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量处理参访方案图片的增删改操作")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="扫描 images/ 目录 + 对账 media_index, 生成 ops.json 草稿")
    p_plan.set_defaults(func=cmd_plan)

    p_run = sub.add_parser("run", help="执行 ops.json (默认读当前 ops.json)")
    p_run.add_argument(
        "--config", "-c",
        type=str, default=None,
        help=f"配置文件路径 (默认: {OPS_FILE})",
    )
    p_run.set_defaults(func=cmd_run)

    p_show = sub.add_parser("show", help="打印当前 ops.json")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    sys.exit(args.func(args))
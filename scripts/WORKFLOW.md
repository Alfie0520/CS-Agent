# 参访方案数据更新工作流

## 项目背景

这是一个**游学方案管理系统**，用于管理企业参访学习的资源和信息。

**核心功能**：
- 管理标杆企业数据库（企业信息、主题、城市等）
- 管理参访方案中的图片素材（微信永久素材库）

**关键数据文件**：
| 文件 | 用途 | 位置 |
|------|------|------|
| `enterprises.json` | 标杆企业数据库，供给前端展示 | `app/data/enterprises.json` |
| `media_index.json` | 参访方案图片索引，记录微信素材的 media_id | 服务器 `/data/media_index.json` |
| `2026游学资源表.xlsx` | 企业数据源，由业务方提供 | `scripts/enterprise_db/data/` |

**相关API**：
- `POST https://43.129.183.181/api/visit-image` - 处理图片的增删改操作

---

## 远程服务器信息

- **IP**: `43.129.183.181`
- **SSH 用户**: `ubuntu`
- **SSH 密码**: `Alfie000301`
- **媒体索引文件**: `/data/media_index.json`（服务器上的文件）
- **API 地址**: `https://43.129.183.181/api/visit-image`

---

## 项目文件结构

```
CS-Agent/
├── app/
│   └── data/
│       └── enterprises.json          # 标杆企业数据库（前端使用）
├── scripts/
│   ├── image_ops/                   # 图片素材管理
│   │   ├── batch_image_operations.py # 批量图片操作脚本（调用远程API）
│   │   └── data/
│   │       ├── images/             # 图片文件目录
│   │       └── ops.json            # 图片操作配置
│   └── enterprise_db/              # 企业数据管理
│       ├── build_enterprise_db.py   # 从Excel生成JSON的脚本
│       └── data/
│           └── 2026游学资源表.xlsx  # 源数据表格（文件名必须严格匹配）
```

---

## 工作流一：图片素材更新

### 背景
当参访方案需要更新图片时（如新增企业考察点、更换图片），通过此流程更新微信素材库和索引。

**涉及的微信概念**：
- `media_id`：微信永久素材的唯一标识
- `category`：图片分类，命名规则如 `05浙江`、`广东-深圳`、`09河南` 等

### 步骤

#### 步骤1：用户放置图片
用户将需要处理的图片放入 `scripts/image_ops/data/images/` 目录。

**目录结构示例**：
```
scripts/image_ops/data/images/
├── 杭州/
│   ├── 兔宝宝.png
│   └── 恒生电子.png
├── 广东-深圳/
│   └── 华为松山湖.png
└── 09河南/
    └── 胖东来.png
```

**说明**：
- 图片可以按城市/省份分组存放（仅用于组织文件，category 由后续配置决定）
- 支持格式：`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`

放置完成后，告知 agent 需要处理哪些图片。

#### 步骤2：Agent 连接服务器检查现有数据
SSH 登录服务器，查看 `media_index.json` 确认：
- 哪些图片已存在（需要更新还是新增？）
- 需要删除的旧图片的 `media_id`
- 目标 `category` 的正确名称

```python
import paramiko
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('43.129.183.181', username='ubuntu', password='Alfie000301')

# 获取媒体索引
stdin, stdout, stderr = client.exec_command('cat /data/media_index.json')
media_index = json.loads(stdout.read().decode())
print(f"总记录数: {len(media_index)}")

# 查找特定企业
for item in media_index:
    if '企业名' in item.get('image_name', ''):
        print(item)

# 查看所有 category 及其数量
categories = {}
for item in media_index:
    cat = item.get('category', 'Unknown')
    categories[cat] = categories.get(cat, 0) + 1
for cat, count in sorted(categories.items()):
    print(f"  {cat}: {count}")
```

#### 步骤3：向用户确认操作
向用户确认：
- 每张图片是**新增**还是**更新**
- 对应的企业名称和所在城市（用于确定正确的 `category`）
- 是否需要**删除**某些旧图片（需提供 `media_id`）

**常见问题**：
- 如果图片中的企业在 `enterprises.json` 中已存在，category 通常与该企业的城市对应
- 如果不确定 category，可以先在服务器上搜索同名企业的记录

#### 步骤4：把图片放到正确的子目录 + 自动生成 ops.json

**不要手编 ops.json**，让 agent 跑 `plan` 命令自动生成：

```
scripts/image_ops/data/images/
├── 11山东/          ← 子目录名 = category
│   ├── 潍柴动力.png
│   └── 福瑞达.png
├── 16陕西/
│   └── 中科西光航天.png
├── 广东-东莞/
│   ├── 徐福记透明工厂.png
│   └── 厨邦博览馆.png
├── 02上海/
│   └── 振华重工.png
└── 15安徽/
    ├── 国轩高科.png
    └── 国盾量子.png
```

> ⚠️ 图必须放在子目录里，**子目录名 = category**。如果直接放在 `images/` 根目录，`plan` 会拒绝（无法推断 category）。

**生成 ops.json 草稿：**

```bash
python3 scripts/image_ops/batch_image_operations.py plan
```

`plan` 子命令会：
1. 扫描 `data/images/` 下的子目录和图片
2. 拉取服务器 `/data/media_index.json` 对账
3. **同名同 category → 自动生成 `update` + 填入现有 `media_id`**
4. **本地新增 → 自动生成 `create`**
5. **服务器有但本地无 → 列在 `stale_on_server`，不自动生成 delete（避免误删）**
6. 保留 ops.json 里现有的 `delete` 操作（防止 plan 误覆盖）
7. 写入 `scripts/image_ops/data/ops.json`

**生成的 ops.json 长这样：**

```json
{
  "operations": [
    {
      "operation": "create",
      "image_path": "images/16陕西/中科西光航天.png",
      "image_name": "中科西光航天.png",
      "category": "16陕西",
      "_reason": "本地新增 -> 上传到微信"
    },
    {
      "operation": "update",
      "image_path": "images/11山东/潍柴动力.png",
      "image_name": "潍柴动力.png",
      "category": "11山东",
      "media_id": "Ef5Dol7F8P0PVnRRbx519NbVvONXuyQ2qHDc9FqT2Ni4ADV-GBnrBMo6jS-32yo8",
      "_reason": "同名同 category, 服务器已存在 -> 覆盖"
    }
  ],
  "stale_on_server": [
    {
      "image_name": "京东亚洲一号.png",
      "category": "广东-东莞",
      "media_id": "...",
      "_reason": "服务器有, 本地无 -> 如要删除请手动加 delete 操作"
    }
  ]
}
```

**如果需要删除某张图**（即 `stale_on_server` 中的某条），手动在 `operations` 数组里加一条：

```json
{
  "operation": "delete",
  "media_id": "Ef5Do..."
}
```

#### 步骤5：检查 ops.json 后执行
```bash
# 看一眼 ops.json 当前内容
python3 scripts/image_ops/batch_image_operations.py show

# 确认无误后执行
python3 scripts/image_ops/batch_image_operations.py run
```

**脚本行为**：
1. 读取 `ops.json` 配置
2. 对每张图片进行压缩（目标 200KB 以内）
3. 调用远程 API 上传/更新/删除（`/api/visit-image`）
4. 对 create/update，**额外**调 `/api/assets/image` 同步本地资产库（让 agent 能搜到）
5. 输出执行结果

#### 步骤6：验证服务器结果
再次连接服务器，检查 `media_index.json` 是否正确更新：

```python
stdin, stdout, stderr = client.exec_command('cat /data/media_index.json')
media_index = json.loads(stdout.read().decode())
print(f"总记录数: {len(media_index)}")

# 验证新增的图片是否存在
for item in media_index:
    if '兔宝宝' in item.get('image_name', ''):
        print(f"新增成功: {item}")
```

#### 步骤7：验证本地资产库同步（关键步骤）

> ⚠️ **不要跳过这一步**！
>
> `batch_image_operations.py` 现在会做两件事：
> 1. 调 `/api/visit-image` → 写微信素材库 + `media_index.json`
> 2. 调 `/api/assets/image` → 写本地 `/data/cs-agent-assets/images/` + rescan `asset_index.json`
>
> 但**只有 `media_index.json` 还不够**：客服 agent 的 `send_visit_scheme_assets`
> 工具查的是本地 `asset_index.json`（见 `app/assets/index.py`），
> 历史上因此翻车过（5 月底重构后，13 张新图都查不到）。
>
> 验证方法（搜任意一张本轮新增的图）：

```python
import httpx
r = httpx.get(
    "https://43.129.183.181/api/assets/search",
    params={"query": "兔宝宝"},
    headers={"X-API-Key": "<api_key>"},
    verify=False,
)
print(r.json())  # count >= 1 才对
```

如果发现新增图查不到（说明 batch_image_operations.py 同步本地这一步失败了），
可以手动重灌：

```bash
# 全量重灌：从 media_index 拉全部图片到本地 + rescan
export CS_AGENT_BASE_URL="https://43.129.183.181"
export CS_AGENT_API_KEY="<api_key>"
./agent_maintenance/scripts/restore_assets.sh
```

---

## 工作流二：企业数据更新

### 背景
当业务方提供新的 `2026游学资源表.xlsx` 时，需要将其转换为 `enterprises.json` 供前端使用。

### 前置条件
工作流一（图片更新）已成功完成。

### 步骤

#### 步骤1：向用户确认
询问用户 `scripts/enterprise_db/data/` 目录下的表格是否是最新的。

如果用户确认有新表格，继续步骤2。

#### 步骤2：检查并重命名文件（如需要）
如果文件名不是 `2026游学资源表.xlsx`，需要重命名：
```bash
mv "2026游学资源表(1).xlsx" "2026游学资源表.xlsx"
```

#### 步骤3：运行脚本
```bash
cd /path/to/CS-Agent
python3 scripts/enterprise_db/build_enterprise_db.py
```

**脚本行为**：
1. 读取 Excel 文件的 "标杆企业" 工作表
2. 解析企业数据（编号、城市、名称、主题等）
3. 生成 JSON 文件到 `app/data/enterprises.json`
4. 输出记录数量

#### 步骤4：发布到远程服务器（关键步骤）

> ⚠️ **不要**直接 `git pull` 或 `scp` 把 `app/data/enterprises.json` 推到服务器！
>
> 服务实际加载的运行时数据路径是 **`/data/cs-agent-data/enterprises.json`**（在 `app/config.py:44` 配置），
> 跟代码内置的 `app/data/enterprises.json` 是**两份独立的数据**。只改 `git` 仓库那份，
> 服务读到的还是旧数据（历史上因此翻车过，6 月 5 日之后的新增企业全部查不到）。
>
> 正确做法是调用 HTTP API `/api/enterprises/data`（API 内部会把数据写入运行时路径）：

```bash
# 必须设置这两个环境变量
export CS_AGENT_BASE_URL="https://43.129.183.181"
export CS_AGENT_API_KEY="<从运维获取>"

# 1) 先 dry-run 验证（推荐）
./agent_maintenance/scripts/validate_enterprises.sh app/data/enterprises.json

# 2) 验证通过后再正式发布
./agent_maintenance/scripts/publish_enterprises.sh app/data/enterprises.json
```

或者一行搞定 build + validate + publish：

```bash
./agent_maintenance/scripts/update_enterprises.sh \
  scripts/enterprise_db/data/2026游学资源表.xlsx
```

#### 步骤5：验证结果
脚本会输出类似：
```
完成：共写入 415 条企业数据 → /Users/alfie/vibe_coding/CS-Agent/app/data/enterprises.json
{"success": true, "count": 415, "source_path": "/data/cs-agent-data/enterprises.json"}
```

可以对比新旧版本的差异，并 curl 服务器看运行时数据是否已更新：

```python
import json

with open('app/data/enterprises.json') as f:
    new = json.load(f)

print(f"本地记录数: {len(new)}")
print(f"最新ID: {max(e['id'] for e in new)}")
```

```bash
# 看运行时数据是否已更新
curl -fsS -H "X-API-Key: $CS_AGENT_API_KEY" \
  "$CS_AGENT_BASE_URL/api/enterprises/data" | python3 -c "import sys,json; d=json.load(sys.stdin); print('远端记录数:', d['count'])"
```

---

## 两个工作流的关系

工作流一和工作流二是**串行执行**的：

```
用户放置图片
    ↓
工作流一：图片更新
    ↓（成功后）
向用户确认表格是否更新
    ↓
工作流二：企业数据更新
    ↓
完成
```

通常业务方更新企业数据时，也会同步更新参访方案图片，所以两者需要按顺序执行。

---

## 技术细节

### 图片压缩
- 目标大小：200KB 以内
- 压缩策略：
  1. 逐步缩小尺寸（100% → 50% → 25% → 10%）
  2. 逐步降低质量（85 → 70 → 55 → 40 → 30）
  3. 最终质量 20%

### API Key
`batch_image_operations.py` 中硬编码了 API Key：
```python
REMOTE_API_KEY = "cRgCWNHkfrZt7GE47JQtyE9RDY2Pxo4lAs9DQjuSXUY="
```
用于认证请求到远程 API。

### SSL 证书
服务器使用 HTTPS 但证书是颁发给域名的，直接用 IP 访问会证书验证失败。脚本中已设置 `verify=False` 跳过验证。

### 服务器权限
`/data/media_index.json` 文件所有者是 `root`，权限 `644`。如果遇到写入问题，在服务器上执行：
```bash
sudo chmod 666 /data/media_index.json
```

---

## 快速命令参考

```bash
# 图片更新
python3 scripts/image_ops/batch_image_operations.py

# 企业数据更新（本地）
python3 scripts/enterprise_db/build_enterprise_db.py

# 发布到服务器（自动写运行时数据）
./agent_maintenance/scripts/publish_enterprises.sh app/data/enterprises.json

# 一行完成：build + validate + publish
./agent_maintenance/scripts/update_enterprises.sh scripts/enterprise_db/data/2026游学资源表.xlsx

# SSH 连接服务器
ssh ubuntu@43.129.183.181
# 密码: Alfie000301
```
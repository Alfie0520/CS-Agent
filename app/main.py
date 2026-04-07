import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.config import get_settings
from app.core.security import check_signature
from app.core.xml_parser import build_transfer_kf_xml, parse_xml
from app.handler.router import dispatch
from app.models.message import MsgType
from app.visit_image_api import ImageOperation, process_image_operation
from app.wechat_api.menu import (
    add_conditional_menu,
    create_menu,
    create_menu_from_json_file,
    del_conditional_menu,
    delete_menu,
    get_current_selfmenu_info,
    get_menu,
    try_match_menu,
)
from app.wechat_api.token_manager import token_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    await token_manager.start()
    logger.info("CS-Agent started")

    menu_file = settings.wechat_menu_file_path
    if menu_file:
        logger.info("Auto-creating WeChat menu from: %s", menu_file)
        result = await create_menu_from_json_file(menu_file)
        if result.get("errcode", 0) == 0:
            logger.info("WeChat menu created successfully")
        else:
            logger.warning("Failed to create WeChat menu: %s", result)

    yield
    await token_manager.stop()
    logger.info("CS-Agent stopped")


app = FastAPI(title="CS-Agent", lifespan=lifespan)

_menus_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>自定义菜单管理</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; color: #333; }
.header { background: #07c160; color: white; padding: 16px 24px; font-size: 18px; font-weight: 600; }
.container { max-width: 1100px; margin: 24px auto; padding: 0 16px; display: grid; grid-template-columns: 340px 1fr; gap: 20px; }
.panel { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 20px; }
.panel-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; color: #555; border-bottom: 1px solid #eee; padding-bottom: 10px; }
.btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: opacity 0.2s; }
.btn:hover { opacity: 0.85; }
.btn-primary { background: #07c160; color: white; }
.btn-danger { background: #ff4d4f; color: white; }
.btn-secondary { background: #e8e8e8; color: #555; }
.btn-sm { padding: 5px 12px; font-size: 13px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; color: #666; margin-bottom: 4px; }
.form-group input, .form-group select { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
.form-group input:focus, .form-group select:focus { outline: none; border-color: #07c160; }
.msg { padding: 10px 14px; border-radius: 4px; margin-bottom: 14px; font-size: 14px; display: none; }
.msg-success { background: #f6ffed; border: 1px solid #b7eb8f; color: #52c41a; }
.msg-error { background: #fff2f0; border: 1px solid #ffccc7; color: #ff4d4f; }
.hidden { display: none; }
.menu-item { border: 1px solid #e8e8e8; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; cursor: pointer; transition: all 0.15s; }
.menu-item:hover { border-color: #07c160; background: #f6fff7; }
.menu-item.active { border-color: #07c160; background: #eaf7ef; }
.menu-item-name { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.menu-item-meta { font-size: 12px; color: #999; }
.sub-items { margin-top: 6px; padding-left: 12px; border-left: 2px solid #e8e8e8; }
.sub-item { font-size: 13px; padding: 4px 0; color: #555; }
.empty { text-align: center; color: #999; padding: 32px 0; font-size: 14px; }
.actions { display: flex; gap: 8px; margin-top: 14px; }
.row { display: flex; gap: 12px; }
.row .form-group { flex: 1; }
.tips { font-size: 12px; color: #999; margin-top: 4px; }
</style>
</head>
<body>
<div class="header">🛠 自定义菜单管理</div>
<div class="container">
  <div>
    <div class="panel">
      <div class="panel-title">当前菜单结构</div>
      <div id="menuList"><div class="empty">加载中...</div></div>
    </div>
    <div class="panel" style="margin-top:16px;">
      <div class="panel-title">操作</div>
      <div class="actions">
        <button class="btn btn-primary" onclick="refreshMenu()">🔄 刷新</button>
        <button class="btn btn-danger" onclick="deleteMenu()">🗑 删除菜单</button>
      </div>
      <div id="actionMsg" class="msg" style="margin-top:12px;"></div>
    </div>
  </div>
  <div>
    <div class="panel">
      <div class="panel-title" id="editorTitle">编辑按钮</div>
      <div id="editorPanel">
        <div class="form-group">
          <label>按钮名称</label>
          <input type="text" id="btnName" placeholder="如：产品手册" maxlength="16">
          <div class="tips">最多8个汉字或16个字母</div>
        </div>
        <div class="form-group">
          <label>按钮类型</label>
          <select id="btnType" onchange="onTypeChange()">
            <option value="view">跳转网页 (view)</option>
            <option value="click">点击事件 (click)</option>
          </select>
        </div>
        <div class="form-group" id="urlGroup">
          <label>跳转链接</label>
          <input type="text" id="btnUrl" placeholder="https://example.com">
        </div>
        <div class="form-group hidden" id="keyGroup">
          <label>事件 Key</label>
          <input type="text" id="btnKey" placeholder="如：MENU_QUOTE">
          <div class="tips">用户点击后，微信会推送 EventKey 为此值的点击事件</div>
        </div>
        <div class="form-group hidden" id="mediaIdGroup">
          <label>素材 Media ID</label>
          <input type="text" id="btnMediaId" placeholder="永久素材的 media_id">
        </div>
        <div class="form-group">
          <label>所属一级菜单</label>
          <select id="parentMenu"><option value="">作为一级菜单</option></select>
          <div class="tips">留空则创建为一级菜单（一级菜单最多3个）</div>
        </div>
        <div style="display:flex;gap:8px;margin-top:14px;">
          <button class="btn btn-primary" onclick="saveButton()">💾 保存</button>
          <button class="btn btn-secondary" onclick="clearEditor()">清空</button>
        </div>
        <div id="editMsg" class="msg" style="margin-top:12px;"></div>
      </div>
    </div>
    <div class="panel" style="margin-top:16px;">
      <div class="panel-title">💡 快速操作</div>
      <div style="font-size:13px;color:#666;line-height:1.8;">
        <p>• 修改后点「保存」会立即同步到微信公众号</p>
        <p>• 一级菜单最多 <strong>3个</strong>，每个一级菜单下子按钮最多 <strong>5个</strong></p>
        <p>• 删除菜单后，公众号底部菜单将变为空白</p>
      </div>
    </div>
  </div>
</div>
<script>
let currentMenu = null;
let editIndex = null;      // [parentIndex, subIndex] if editing sub; [index] if editing parent
let isEditingSub = false;

const apiBase = window.location.origin;

async function api(formData) {
  const resp = await fetch(apiBase + '/api/menu', { method: 'POST', body: new URLSearchParams(formData) });
  return resp.json();
}

async function getMenu() {
  const resp = await fetch(apiBase + '/api/menu');
  return resp.json();
}

function showMsg(el, text, type) {
  el.textContent = text;
  el.className = 'msg msg-' + type;
  el.style.display = 'block';
  if (type === 'success') setTimeout(() => el.style.display = 'none', 3000);
}

function renderMenuList(data) {
  const list = document.getElementById('menuList');
  if (!data || !data.menu || !data.menu.button || data.menu.button.length === 0) {
    list.innerHTML = '<div class="empty">暂无菜单配置</div>';
    return;
  }
  const buttons = data.menu.button;
  let html = '';
  buttons.forEach((btn, i) => {
    const subs = btn.sub_button || [];
    html += '<div class="menu-item" onclick="editParent(' + i + ')">';
    html += '<div class="menu-item-name">' + btn.name + '</div>';
    html += '<div class="menu-item-meta">' + (btn.type || '一级菜单') + ' | ' + subs.length + ' 个子按钮</div>';
    if (subs.length > 0) {
      html += '<div class="sub-items">';
      subs.forEach((sub, j) => {
        html += '<div class="sub-item" onclick="event.stopPropagation();editSub(' + i + ',' + j + ')">· ' + sub.name + ' (' + (sub.type || '子菜单') + ')</div>';
      });
      html += '</div>';
    }
    html += '</div>';
  });
  list.innerHTML = html;

  // update parent select
  const sel = document.getElementById('parentMenu');
  sel.innerHTML = '<option value="">作为一级菜单</option>';
  buttons.forEach((btn, i) => {
    sel.innerHTML += '<option value="' + i + '">' + btn.name + '</option>';
  });
}

function clearEditor() {
  editIndex = null; isEditingSub = false;
  document.getElementById('btnName').value = '';
  document.getElementById('btnType').value = 'view';
  document.getElementById('btnUrl').value = '';
  document.getElementById('btnKey').value = '';
  document.getElementById('btnMediaId').value = '';
  document.getElementById('parentMenu').value = '';
  document.getElementById('editorTitle').textContent = '新增按钮';
  onTypeChange();
}

function editParent(idx) {
  const btn = currentMenu.menu.button[idx];
  editIndex = idx; isEditingSub = false;
  document.getElementById('btnName').value = btn.name || '';
  document.getElementById('btnType').value = btn.type || 'view';
  document.getElementById('btnUrl').value = btn.url || '';
  document.getElementById('btnKey').value = btn.key || '';
  document.getElementById('btnMediaId').value = btn.media_id || '';
  document.getElementById('parentMenu').value = '';
  document.getElementById('editorTitle').textContent = '编辑一级菜单：' + btn.name;
  onTypeChange();
}

function editSub(parentIdx, subIdx) {
  const btn = currentMenu.menu.button[parentIdx].sub_button[subIdx];
  editIndex = [parentIdx, subIdx]; isEditingSub = true;
  document.getElementById('btnName').value = btn.name || '';
  document.getElementById('btnType').value = btn.type || 'view';
  document.getElementById('btnUrl').value = btn.url || '';
  document.getElementById('btnKey').value = btn.key || '';
  document.getElementById('btnMediaId').value = btn.media_id || '';
  document.getElementById('parentMenu').value = String(parentIdx);
  document.getElementById('editorTitle').textContent = '编辑子按钮：' + btn.name;
  onTypeChange();
}

function onTypeChange() {
  const t = document.getElementById('btnType').value;
  document.getElementById('urlGroup').classList.toggle('hidden', t !== 'view');
  document.getElementById('keyGroup').classList.toggle('hidden', t !== 'click');
  document.getElementById('mediaIdGroup').classList.toggle('hidden', t !== 'media_id' && t !== 'miniprogram');
}

async function saveButton() {
  const name = document.getElementById('btnName').value.trim();
  if (!name) { showMsg(document.getElementById('editMsg'), '按钮名称不能为空', 'error'); return; }
  const type = document.getElementById('btnType').value;
  const url = document.getElementById('btnUrl').value.trim();
  const key = document.getElementById('btnKey').value.trim();
  const mediaId = document.getElementById('btnMediaId').value.trim();
  const parentIdx = document.getElementById('parentMenu').value;

  if (!currentMenu) { showMsg(document.getElementById('editMsg'), '请先刷新获取当前菜单', 'error'); return; }
  const buttons = currentMenu.menu.button;

  let newBtn = { name, type };
  if (type === 'view') newBtn.url = url || 'https://';
  else if (type === 'click') newBtn.key = key || ('MENU_' + Date.now());
  else if (type === 'media_id') newBtn.media_id = mediaId;

  if (parentIdx === '' || parentIdx === null) {
    // 一级菜单
    if (editIndex !== null && !isEditingSub) {
      buttons[editIndex] = newBtn;
    } else {
      if (buttons.length >= 3) { showMsg(document.getElementById('editMsg'), '一级菜单最多3个', 'error'); return; }
      buttons.push(newBtn);
    }
  } else {
    const pi = parseInt(parentIdx);
    if (!buttons[pi].sub_button) buttons[pi].sub_button = [];
    if (isEditingSub && Array.isArray(editIndex)) {
      buttons[pi].sub_button[editIndex[1]] = newBtn;
    } else {
      if (buttons[pi].sub_button.length >= 5) { showMsg(document.getElementById('editMsg'), '子按钮最多5个', 'error'); return; }
      buttons[pi].sub_button.push(newBtn);
    }
  }

  const payload = JSON.stringify({ button: buttons });
  const formData = new URLSearchParams({ operation: 'create', menu_data: payload });
  const result = await api(formData);
  if (result.errcode === 0) {
    showMsg(document.getElementById('editMsg'), '保存成功！', 'success');
    clearEditor();
    refreshMenu();
  } else {
    showMsg(document.getElementById('editMsg'), '保存失败：' + result.errmsg, 'error');
  }
}

async function refreshMenu() {
  const data = await getMenu();
  if (data.errcode) {
    document.getElementById('menuList').innerHTML = '<div class="empty">加载失败：' + data.errmsg + '</div>';
    return;
  }
  currentMenu = data;
  renderMenuList(data);
  showMsg(document.getElementById('actionMsg'), '刷新成功', 'success');
}

async function deleteMenu() {
  if (!confirm('确定删除当前自定义菜单吗？删除后公众号底部菜单将变为空白。')) return;
  const result = await api(new URLSearchParams({ operation: 'delete' }));
  if (result.errcode === 0) {
    showMsg(document.getElementById('actionMsg'), '菜单已删除', 'success');
    refreshMenu();
  } else {
    showMsg(document.getElementById('actionMsg'), '删除失败：' + result.errmsg, 'error');
  }
}

refreshMenu();
</script>
</body>
</html>
"""


@app.get("/wx", response_class=PlainTextResponse)
async def verify_token(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """微信服务器首次配置验证：校验签名后原样返回 echostr。"""
    settings = get_settings()
    if check_signature(signature, timestamp, nonce, settings.wechat_token):
        return echostr
    return "invalid signature"


@app.post("/wx")
async def receive_message(request: Request, background_tasks: BackgroundTasks):
    """接收微信推送的消息/事件。
    - 转人工客服：同步返回 transfer_customer_service XML（仅此场景需要被动回复）
    - 其他消息：立即返回 success，异步通过客服消息接口回复
    """
    body = await request.body()

    try:
        msg = parse_xml(body)
        if (
            msg.msg_type == MsgType.TEXT
            and (msg.content or "").strip() == "转人工"
        ):
            xml = build_transfer_kf_xml(
                to_user=msg.from_user, from_user=msg.to_user
            )
            return Response(content=xml, media_type="application/xml")
    except Exception:
        logger.exception("Failed to check passive reply condition")

    background_tasks.add_task(dispatch, body)
    return PlainTextResponse("success")


@app.post("/api/visit-image")
async def manage_visit_image(
    operation: str = Form(...),
    image_name: str | None = Form(None),
    category: str | None = Form(None),
    base64_data: str | None = Form(None),
    media_id: str | None = Form(None),
    api_key: str | None = Form(None),
):
    """参访方案图片增删改接口。

    完整流程：上传到微信服务器 → 获取 media_id → 更新索引（删除旧记录）→ 返回结果

    Args:
        operation: 操作类型，"create" | "update" | "delete"
        image_name: 图片文件名（如 "胖东来.png"），create/update 时必填
        category: 分类/地理位置（如 "09河南"），create/update 时必填
        base64_data: 图片的 base64 编码字符串，create/update 时必填
        media_id: 要操作的素材 media_id，update/delete 时必填
        api_key: API 访问密钥，必须与环境变量中的 API_KEY 匹配

    Returns:
        {
            "success": bool,
            "operation": str,
            "media_id": str (新增/更新后),
            "image_name": str,
            "category": str,
            "error": str (失败时)
        }
    """
    settings = get_settings()
    expected_key = getattr(settings, "visit_image_api_key", None)
    if expected_key and api_key != expected_key:
        return {"success": False, "error": "Invalid API key"}

    result = await process_image_operation(
        operation=operation,
        image_name=image_name,
        category=category,
        base64_data=base64_data,
        media_id=media_id,
    )
    return result


@app.get("/admin/menu")
async def menu_admin_page():
    """菜单管理后台页面（仅供内部使用）。"""
    return HTMLResponse(_menus_html)


@app.get("/api/menu")
async def get_menu_api():
    """获取当前菜单配置。"""
    return await get_menu()


@app.post("/api/menu")
async def manage_menu(
    operation: str = Form(...),
    menu_file_path: str | None = Form(None),
    menu_data: str | None = Form(None),
    api_key: str | None = Form(None),
):
    """自定义菜单增删改查接口（供 Postman 调用）。

    Args:
        operation: 操作类型
            - "create": 从文件或 JSON 创建菜单（默认）
            - "get": 查询当前菜单配置
            - "delete": 删除当前菜单
            - "get_selfmenu": 获取当前使用的自定义菜单配置
            - "create_conditional": 创建个性化菜单（需传 menu_data）
            - "delete_conditional": 删除个性化菜单（需传 menu_data 中的 menuid）
            - "try_match": 测试个性化菜单匹配（需传 menu_data 中的 user_id）
        menu_file_path: 菜单 JSON 文件路径，operation=create 时使用（优先级高于 menu_data）
        menu_data: JSON 字符串，个性化菜单操作时需要传入
        api_key: API 访问密钥，必须与环境变量中的 API_KEY 匹配

    Returns:
        微信 API 的原始响应 JSON
    """
    settings = get_settings()
    expected_key = getattr(settings, "menu_api_key", None)
    if expected_key and api_key != expected_key:
        return {"success": False, "error": "Invalid API key"}

    if operation == "get":
        return await get_menu()
    elif operation == "delete":
        return await delete_menu()
    elif operation == "get_selfmenu":
        return await get_current_selfmenu_info()
    elif operation == "create_conditional":
        if not menu_data:
            return {"success": False, "error": "个性化菜单创建需要传入 menu_data"}
        import json
        return await add_conditional_menu(json.loads(menu_data))
    elif operation == "delete_conditional":
        if not menu_data:
            return {"success": False, "error": "删除个性化菜单需要传入 menu_data"}
        import json
        return await del_conditional_menu(json.loads(menu_data)["menuid"])
    elif operation == "try_match":
        if not menu_data:
            return {"success": False, "error": "测试个性化菜单匹配需要传入 menu_data"}
        import json
        return await try_match_menu(json.loads(menu_data)["user_id"])
    elif operation == "create":
        if menu_file_path:
            return await create_menu_from_json_file(menu_file_path)
        elif menu_data:
            import json
            return await create_menu(json.loads(menu_data))
        else:
            return {"success": False, "error": "创建菜单需要传入 menu_file_path 或 menu_data"}
    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}


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
.header { background: #07c160; color: white; padding: 16px 24px; font-size: 18px; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
.header span { font-size: 13px; font-weight: 400; opacity: 0.8; }
.container { max-width: 1200px; margin: 24px auto; padding: 0 16px; display: grid; grid-template-columns: 380px 1fr; gap: 20px; }
.panel { background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 20px; }
.panel-title { font-size: 15px; font-weight: 600; margin-bottom: 14px; color: #555; border-bottom: 1px solid #eee; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
.btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; transition: opacity 0.2s; white-space: nowrap; }
.btn:hover { opacity: 0.85; }
.btn-primary { background: #07c160; color: white; }
.btn-danger { background: #ff4d4f; color: white; }
.btn-secondary { background: #e8e8e8; color: #555; }
.btn-outline { background: white; border: 1px solid #ddd; color: #555; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn-xs { padding: 2px 8px; font-size: 11px; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; color: #666; margin-bottom: 4px; }
.form-group input, .form-group select, .form-group textarea { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
.form-group textarea { resize: vertical; min-height: 60px; }
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: #07c160; }
.msg { padding: 10px 14px; border-radius: 4px; margin-bottom: 14px; font-size: 14px; display: none; line-height: 1.5; }
.msg-success { background: #f6ffed; border: 1px solid #b7eb8f; color: #52c41a; }
.msg-error { background: #fff2f0; border: 1px solid #ffccc7; color: #ff4d4f; }
.hidden { display: none; }
.menu-item { border: 1px solid #e8e8e8; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; cursor: pointer; transition: all 0.15s; position: relative; }
.menu-item:hover { border-color: #07c160; background: #f6fff7; }
.menu-item.active { border-color: #07c160; background: #eaf7ef; }
.menu-item.row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; }
.menu-item-name { font-weight: 600; font-size: 14px; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.menu-item-meta { font-size: 11px; color: #999; flex-shrink: 0; }
.sub-items { margin-top: 4px; padding-left: 12px; border-left: 2px solid #e8e8e8; }
.sub-item { font-size: 13px; padding: 4px 8px; color: #555; border-radius: 4px; cursor: pointer; display: flex; align-items: center; gap: 6px; }
.sub-item:hover { background: #f0f7f2; color: #07c160; }
.sub-item.active { background: #eaf7ef; color: #07c160; }
.empty { text-align: center; color: #999; padding: 32px 0; font-size: 14px; }
.actions { display: flex; gap: 8px; margin-top: 14px; flex-wrap: wrap; }
.tips { font-size: 12px; color: #999; margin-top: 4px; }
.badge { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; }
.badge-primary { background: #eaf7ef; color: #07c160; }
.badge-gray { background: #f5f5f5; color: #999; }
.badge-red { background: #fff2f0; color: #ff4d4f; }
.edit-mode-tag { font-size: 12px; color: #07c160; font-weight: 400; }
.section-gap { margin-top: 16px; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.type-desc { font-size: 11px; color: #999; margin-top: 2px; }
hr.divider { border: none; border-top: 1px solid #eee; margin: 14px 0; }
</style>
</head>
<body>
<div class="header">
  <div>🛠 自定义菜单管理</div>
  <span>bgtx.work/admin/menu</span>
</div>
<div class="container">
  <!-- 左侧：菜单树 -->
  <div>
    <div class="panel">
      <div class="panel-title">
        当前菜单结构
        <button class="btn btn-primary btn-sm" onclick="newParent()">+ 新增一级菜单</button>
      </div>
      <div id="menuList"><div class="empty">加载中...</div></div>
    </div>

    <div class="panel section-gap">
      <div class="panel-title">操作</div>
      <div class="actions">
        <button class="btn btn-secondary" onclick="refreshMenu()">🔄 刷新</button>
        <button class="btn btn-danger" onclick="deleteMenu()">🗑 删除全部菜单</button>
      </div>
      <div id="actionMsg" class="msg" style="margin-top:12px;"></div>
    </div>

    <div class="panel section-gap">
      <div class="panel-title">💡 说明</div>
      <div style="font-size:13px;color:#666;line-height:2;">
        <p>• 一级菜单最多 <strong>3个</strong></p>
        <p>• 每个一级菜单下子按钮最多 <strong>5个</strong></p>
        <p>• 按钮名称：最多<strong>8个汉字</strong>或<strong>16个字母</strong></p>
        <p>• 点卡片直接编辑，保存后<strong>实时同步</strong>到公众号</p>
      </div>
    </div>
  </div>

  <!-- 右侧：编辑表单 -->
  <div>
    <div class="panel">
      <div class="panel-title">
        <span id="editorTitle">新增 / 编辑按钮</span>
        <span id="editModeTag" class="edit-mode-tag hidden">编辑中</span>
      </div>
      <div id="editorPanel">
        <div class="form-group">
          <label>按钮名称</label>
          <input type="text" id="btnName" placeholder="如：产品手册" maxlength="16">
          <div class="tips" id="nameTips">最多8个汉字或16个字母</div>
        </div>

        <div class="form-group">
          <label>按钮类型</label>
          <select id="btnType" onchange="onTypeChange()">
            <option value="view">跳转网页 (view)</option>
            <option value="click">点击事件 (click)</option>
            <option value="miniprogram">跳转小程序 (miniprogram)</option>
            <option value="media_id">发送永久素材 (media_id)</option>
            <option value="location_select">弹出地理位置 (location_select)</option>
            <option value="scancode_push">扫码推事件 (scancode_push)</option>
            <option value="scancode_waitmsg">扫码推事件(待回复) (scancode_waitmsg)</option>
            <option value="pic_sysphoto">拍照发图 (pic_sysphoto)</option>
            <option value="pic_photo_or_album">拍照/相册发图 (pic_photo_or_album)</option>
            <option value="pic_weixin">相册发图器 (pic_weixin)</option>
          </select>
        </div>

        <!-- view 类型 -->
        <div class="form-group" id="urlGroup">
          <label>跳转链接 <span class="badge badge-primary">必填</span></label>
          <input type="text" id="btnUrl" placeholder="https://example.com">
          <div class="tips">用户点击后跳转到此 URL</div>
        </div>

        <!-- click / scancode / pic 类型 -->
        <div class="form-group hidden" id="keyGroup">
          <label>事件 Key <span class="badge badge-primary">必填</span></label>
          <input type="text" id="btnKey" placeholder="如：MENU_QUOTE">
          <div class="tips">用户点击后，微信会推送 EventKey 为此值的点击事件</div>
        </div>

        <!-- media_id 类型 -->
        <div class="form-group hidden" id="mediaIdGroup">
          <label>素材 Media ID <span class="badge badge-primary">必填</span></label>
          <input type="text" id="btnMediaId" placeholder="永久素材的 media_id">
          <div class="tips">发送永久素材（图文、图片、音频、视频）</div>
        </div>

        <!-- miniprogram 类型 -->
        <div class="hidden" id="miniprogramGroup">
          <div class="two-col">
            <div class="form-group">
              <label>小程序 AppID <span class="badge badge-primary">必填</span></label>
              <input type="text" id="btnAppid" placeholder="wx1234567890abcdef">
            </div>
            <div class="form-group">
              <label>小程序页面路径 <span class="badge badge-primary">必填</span></label>
              <input type="text" id="btnPagepath" placeholder="pages/index/index">
            </div>
          </div>
          <div class="form-group">
            <label>备用网页 URL</label>
            <input type="text" id="btnUrl2" placeholder="https://example.com（用户无法访问小程序时跳转）">
          </div>
        </div>

        <hr class="divider">

        <div class="form-group">
          <label>所属一级菜单</label>
          <select id="parentMenu" onchange="onParentChange()">
            <option value="">作为一级菜单（无上级）</option>
          </select>
          <div class="tips" id="parentTips">作为一级菜单时，一级菜单最多3个；作为子菜单时，最多5个</div>
        </div>

        <hr class="divider">

        <div style="display:flex;gap:8px;">
          <button class="btn btn-primary" id="saveBtn" onclick="saveButton()">💾 保存并发布</button>
          <button class="btn btn-secondary" onclick="clearEditor()">清空</button>
        </div>
        <div id="editMsg" class="msg" style="margin-top:12px;"></div>
      </div>
    </div>
  </div>
</div>

<script>
let currentMenu = null;
let editPath = null; // null=新增, [i]=编辑一级, [i,j]=编辑子级

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

function typeLabel(type) {
  const map = {
    view: '🌐', click: '🔘', miniprogram: '📱',
    media_id: '🖼', location_select: '📍', scancode_push: '📷',
    scancode_waitmsg: '📷', pic_sysphoto: '📸',
    pic_photo_or_album: '📷', pic_weixin: '🖼'
  };
  return map[type] || type;
}

function renderMenuList(data) {
  const list = document.getElementById('menuList');
  if (!data || !data.menu || !data.menu.button || data.menu.button.length === 0) {
    list.innerHTML = '<div class="empty">暂无菜单配置<br><br><button class="btn btn-primary btn-sm" onclick="newParent()">+ 新增第一个一级菜单</button></div>';
    updateParentSelect([]);
    return;
  }
  const buttons = data.menu.button;
  let html = '';
  buttons.forEach((btn, i) => {
    const subs = btn.sub_button || [];
    const isActive = editPath && editPath[0] === i && editPath.length === 1;
    html += '<div class="menu-item' + (isActive ? ' active' : '') + '">';
    html += '<div class="menu-item row" onclick="editParent(' + i + ')">';
    html += '<span class="menu-item-name">' + btn.name + '</span>';
    html += '<span class="badge badge-gray">' + typeLabel(btn.type) + '</span>';
    html += '<span class="menu-item-meta">' + subs.length + '子</span>';
    html += '<div style="display:flex;gap:2px;flex-shrink:0;">';
    html += '<button class="btn btn-xs btn-outline" onclick="event.stopPropagation();moveUp(' + i + ')">↑</button>';
    html += '<button class="btn btn-xs btn-outline" onclick="event.stopPropagation();moveDown(' + i + ')">↓</button>';
    html += '<button class="btn btn-xs btn-danger" onclick="event.stopPropagation();deleteBtn(' + i + ')">×</button>';
    html += '</div></div>';
    if (subs.length > 0) {
      html += '<div class="sub-items">';
      subs.forEach((sub, j) => {
        const isSubActive = editPath && editPath[0] === i && editPath[1] === j;
        html += '<div class="sub-item' + (isSubActive ? ' active' : '') + '" onclick="editSub(' + i + ',' + j + ')">';
        html += '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + sub.name + '</span>';
        html += '<span class="badge badge-gray" style="flex-shrink:0;">' + typeLabel(sub.type) + '</span>';
        html += '<button class="btn btn-xs btn-danger" onclick="event.stopPropagation();deleteSub(' + i + ',' + j + ')">×</button>';
        html += '</div>';
      });
      html += '</div>';
    }
    html += '</div>';
  });
  list.innerHTML = html;
  updateParentSelect(buttons);
}

function updateParentSelect(buttons) {
  const sel = document.getElementById('parentMenu');
  sel.innerHTML = '<option value="">作为一级菜单（无上级）</option>';
  buttons.forEach((btn, i) => {
    sel.innerHTML += '<option value="' + i + '">' + btn.name + '</option>';
  });
}

function newParent() {
  editPath = null;
  clearEditor();
  document.getElementById('editorTitle').textContent = '新增一级菜单';
  document.getElementById('parentMenu').value = '';
  document.getElementById('parentTips').textContent = '作为一级菜单，最多3个';
  onParentChange();
}

function editParent(idx) {
  if (!currentMenu) return;
  const btn = currentMenu.menu.button[idx];
  editPath = [idx];
  document.getElementById('editorTitle').textContent = '编辑一级菜单';
  document.getElementById('editModeTag').classList.remove('hidden');
  document.getElementById('btnName').value = btn.name || '';
  document.getElementById('btnType').value = btn.type || 'view';
  document.getElementById('btnUrl').value = btn.url || '';
  document.getElementById('btnKey').value = btn.key || '';
  document.getElementById('btnMediaId').value = btn.media_id || '';
  document.getElementById('btnAppid').value = btn.appid || '';
  document.getElementById('btnPagepath').value = btn.pagepath || '';
  document.getElementById('btnUrl2').value = btn.url || '';
  document.getElementById('parentMenu').value = '';
  onTypeChange();
  onParentChange();
  document.getElementById('btnName').focus();
}

function editSub(parentIdx, subIdx) {
  if (!currentMenu) return;
  const btn = currentMenu.menu.button[parentIdx].sub_button[subIdx];
  editPath = [parentIdx, subIdx];
  document.getElementById('editorTitle').textContent = '编辑子菜单';
  document.getElementById('editModeTag').classList.remove('hidden');
  document.getElementById('btnName').value = btn.name || '';
  document.getElementById('btnType').value = btn.type || 'view';
  document.getElementById('btnUrl').value = btn.url || '';
  document.getElementById('btnKey').value = btn.key || '';
  document.getElementById('btnMediaId').value = btn.media_id || '';
  document.getElementById('btnAppid').value = btn.appid || '';
  document.getElementById('btnPagepath').value = btn.pagepath || '';
  document.getElementById('btnUrl2').value = btn.url || '';
  document.getElementById('parentMenu').value = String(parentIdx);
  onTypeChange();
  onParentChange();
  document.getElementById('btnName').focus();
}

function clearEditor() {
  editPath = null;
  document.getElementById('editorTitle').textContent = '新增 / 编辑按钮';
  document.getElementById('editModeTag').classList.add('hidden');
  document.getElementById('btnName').value = '';
  document.getElementById('btnType').value = 'view';
  document.getElementById('btnUrl').value = '';
  document.getElementById('btnKey').value = '';
  document.getElementById('btnMediaId').value = '';
  document.getElementById('btnAppid').value = '';
  document.getElementById('btnPagepath').value = '';
  document.getElementById('btnUrl2').value = '';
  document.getElementById('parentMenu').value = '';
  onTypeChange();
  onParentChange();
}

function onTypeChange() {
  const t = document.getElementById('btnType').value;
  document.getElementById('urlGroup').classList.toggle('hidden', t !== 'view' && t !== 'miniprogram');
  document.getElementById('keyGroup').classList.toggle('hidden', !['click','location_select','scancode_push','scancode_waitmsg','pic_sysphoto','pic_photo_or_album','pic_weixin'].includes(t));
  document.getElementById('mediaIdGroup').classList.toggle('hidden', t !== 'media_id');
  document.getElementById('miniprogramGroup').classList.toggle('hidden', t !== 'miniprogram');
  if (t === 'miniprogram') {
    document.getElementById('urlGroup').classList.remove('hidden');
  }
}

function onParentChange() {
  const parentIdx = document.getElementById('parentMenu').value;
  const tips = document.getElementById('parentTips');
  if (parentIdx === '') {
    tips.textContent = '作为一级菜单，最多3个';
  } else {
    tips.textContent = '作为子菜单，当前一级菜单下最多5个子菜单';
  }
}

function validateChineseLength(str) {
  let len = 0;
  for (let ch of str) { len += ch.charCodeAt(0) > 255 ? 1 : 0.5; }
  return len;
}

async function saveButton() {
  const name = document.getElementById('btnName').value.trim();
  if (!name) { showMsg(document.getElementById('editMsg'), '按钮名称不能为空', 'error'); return; }
  const len = validateChineseLength(name);
  if (len > 8) { showMsg(document.getElementById('editMsg'), '按钮名称最多8个汉字或16个字母，当前过长', 'error'); return; }

  const type = document.getElementById('btnType').value;
  const url = document.getElementById('btnUrl').value.trim();
  const key = document.getElementById('btnKey').value.trim();
  const mediaId = document.getElementById('btnMediaId').value.trim();
  const appid = document.getElementById('btnAppid').value.trim();
  const pagepath = document.getElementById('btnPagepath').value.trim();
  const url2 = document.getElementById('btnUrl2').value.trim();
  const parentIdx = document.getElementById('parentMenu').value;

  if (!currentMenu) { showMsg(document.getElementById('editMsg'), '请刷新获取当前菜单后再操作', 'error'); return; }
  const buttons = JSON.parse(JSON.stringify(currentMenu.menu.button));

  let newBtn = { name, type: type === 'view' && !appid ? 'view' : type };

  if (type === 'view') {
    if (!url) { showMsg(document.getElementById('editMsg'), '跳转链接不能为空', 'error'); return; }
    newBtn.url = url;
  } else if (type === 'click' || type === 'location_select' || type === 'scancode_push' || type === 'scancode_waitmsg' || type === 'pic_sysphoto' || type === 'pic_photo_or_album' || type === 'pic_weixin') {
    if (!key) { showMsg(document.getElementById('editMsg'), '事件 Key 不能为空', 'error'); return; }
    newBtn.key = key;
  } else if (type === 'media_id') {
    if (!mediaId) { showMsg(document.getElementById('editMsg'), '素材 Media ID 不能为空', 'error'); return; }
    newBtn.media_id = mediaId;
  } else if (type === 'miniprogram') {
    if (!appid) { showMsg(document.getElementById('editMsg'), '小程序 AppID 不能为空', 'error'); return; }
    if (!pagepath) { showMsg(document.getElementById('editMsg'), '小程序页面路径不能为空', 'error'); return; }
    newBtn.appid = appid;
    newBtn.pagepath = pagepath;
    if (url2) newBtn.url = url2;
  }

  if (parentIdx === '') {
    if (editPath !== null && editPath.length === 1) {
      buttons[editPath[0]] = newBtn;
    } else {
      if (buttons.length >= 3) { showMsg(document.getElementById('editMsg'), '一级菜单最多3个', 'error'); return; }
      buttons.push(newBtn);
    }
  } else {
    const pi = parseInt(parentIdx);
    if (!buttons[pi].sub_button) buttons[pi].sub_button = [];
    if (editPath !== null && editPath.length === 2 && parseInt(editPath[0]) === pi) {
      buttons[pi].sub_button[editPath[1]] = newBtn;
    } else {
      if (buttons[pi].sub_button.length >= 5) { showMsg(document.getElementById('editMsg'), '子按钮最多5个', 'error'); return; }
      buttons[pi].sub_button.push(newBtn);
    }
  }

  const payload = JSON.stringify({ button: buttons });
  const result = await api(new URLSearchParams({ operation: 'create', menu_data: payload }));
  if (result.errcode === 0) {
    showMsg(document.getElementById('editMsg'), '✅ 保存并发布成功！', 'success');
    clearEditor();
    await refreshMenu();
  } else {
    showMsg(document.getElementById('editMsg'), '❌ 保存失败：' + result.errmsg, 'error');
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
  showMsg(document.getElementById('actionMsg'), '已刷新', 'success');
}

async function deleteMenu() {
  if (!confirm('确定删除全部自定义菜单吗？删除后公众号底部菜单将变为空白。')) return;
  const result = await api(new URLSearchParams({ operation: 'delete' }));
  if (result.errcode === 0) {
    showMsg(document.getElementById('actionMsg'), '✅ 菜单已全部删除', 'success');
    clearEditor();
    await refreshMenu();
  } else {
    showMsg(document.getElementById('actionMsg'), '❌ 删除失败：' + result.errmsg, 'error');
  }
}

async function deleteBtn(idx) {
  if (!confirm('确定删除此一级菜单及其所有子菜单吗？')) return;
  if (!currentMenu) return;
  const buttons = JSON.parse(JSON.stringify(currentMenu.menu.button));
  buttons.splice(idx, 1);
  const result = await api(new URLSearchParams({ operation: 'create', menu_data: JSON.stringify({ button: buttons }) }));
  if (result.errcode === 0) { clearEditor(); await refreshMenu(); }
  else showMsg(document.getElementById('actionMsg'), '❌ 删除失败：' + result.errmsg, 'error');
}

async function deleteSub(parentIdx, subIdx) {
  if (!currentMenu) return;
  const buttons = JSON.parse(JSON.stringify(currentMenu.menu.button));
  buttons[parentIdx].sub_button.splice(subIdx, 1);
  const result = await api(new URLSearchParams({ operation: 'create', menu_data: JSON.stringify({ button: buttons }) }));
  if (result.errcode === 0) { clearEditor(); await refreshMenu(); }
  else showMsg(document.getElementById('actionMsg'), '❌ 删除失败：' + result.errmsg, 'error');
}

async function moveUp(idx) {
  if (!currentMenu || idx === 0) return;
  const buttons = JSON.parse(JSON.stringify(currentMenu.menu.button));
  [buttons[idx - 1], buttons[idx]] = [buttons[idx], buttons[idx - 1]];
  const result = await api(new URLSearchParams({ operation: 'create', menu_data: JSON.stringify({ button: buttons }) }));
  if (result.errcode === 0) await refreshMenu();
}

async function moveDown(idx) {
  if (!currentMenu) return;
  const buttons = currentMenu.menu.button;
  if (idx >= buttons.length - 1) return;
  const newButtons = JSON.parse(JSON.stringify(buttons));
  [newButtons[idx], newButtons[idx + 1]] = [newButtons[idx + 1], newButtons[idx]];
  const result = await api(new URLSearchParams({ operation: 'create', menu_data: JSON.stringify({ button: newButtons }) }));
  if (result.errcode === 0) await refreshMenu();
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


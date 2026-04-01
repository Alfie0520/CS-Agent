# Bug 记录

> 检查日期：2026-04-02
> 状态说明：待修复 / 已修复

---

## 🔴 高危

### #1 httpx.AsyncClient 竞态条件
- **文件**: `app/wechat_api/client.py`
- **问题**: 全局 `_client` 在高并发下可能被多个协程同时初始化，导致多个连接实例并存、连接池失效。`await` 释放 GIL，`if _client is None` 不是原子操作。
- **影响**: 所有微信 API 调用（token、发消息、工具调用）
- **修复方向**: 用 `asyncio.Lock` 保护初始化，或在 FastAPI lifespan 里统一初始化 client。

### #2 /test 指令是公开后门
- **文件**: `app/agent/llm_agent.py`
- **问题**: 任何微信用户发 `/test xxx` 都能完全绕过所有业务规则、SOP 和竞对限制，Agent 会无条件执行任意指令。
- **影响**: 安全漏洞，生产环境下任意用户可滥用。
- **修复方向**: 删除该逻辑，或改为对比白名单 openid 后才允许进入测试模式。

### #3 图片 update 事务不完整
- **文件**: `app/visit_image_api.py`
- **问题**: 新图上传成功、删旧图失败时，返回 `success: False` 但同时返回了 `new_media_id`。本地索引与微信素材库从此不同步，且无回滚机制。
- **影响**: 数据不一致，素材库孤立文件堆积。
- **修复方向**: 删旧图失败时尝试删除已上传的新图（补偿事务），或改为先删后传顺序。

### #4 dedup 字典内存泄漏
- **文件**: `app/handler/router.py`
- **问题**: `_DEDUP_MAX = 5000` 的清理逻辑每次超限只删 1 条，高流量下字典持续膨胀，长时间运行后 OOM。TTL 机制在高吞吐时追不上新增速度。
- **影响**: 长时间运行后内存持续增长。
- **修复方向**: 超限时批量清理（如清到 4000），或直接依赖 TTL 清理而不设硬上限。

---

## 🟡 中危

### #5 token_manager 并发刷新
- **文件**: `app/wechat_api/token_manager.py`
- **问题**: 多个并发请求同时检测到 token 过期，全部调用 `_fetch_token()`，导致重复刷新微信 API。
- **修复方向**: 加 `asyncio.Lock`，刷新期间其他请求等待而非重复发起。

### #6 message_handler 部分回复失败继续发送
- **文件**: `app/handler/message_handler.py`
- **问题**: 多条回复中某条发送失败后 catch 异常继续发其余条，用户收到顺序混乱的不完整回复。
- **修复方向**: 失败时中断后续发送，或记录失败条目后统一处理。

### #7 session_store 并发写入覆盖
- **文件**: `app/agent/session_store.py`
- **问题**: 同一用户并发两条消息时，两个任务各自 serialize 历史后写入，后写覆盖前写，消息历史丢失。
- **修复方向**: 对同一 openid 的写操作加锁（per-user asyncio.Lock）。

### #8 XML 解析未知事件类型静默忽略
- **文件**: `app/core/xml_parser.py`
- **问题**: 未知事件类型赋 `msg.event = None` 且无 log，微信新功能上线后隐形丢失。
- **修复方向**: 至少加 `logger.warning`。

### #9 push_image 未校验 media_id
- **文件**: `app/agent/llm_agent.py`
- **问题**: LLM 传空字符串或格式错误的 media_id 时直接打微信 API，错误信息原样返回。
- **修复方向**: 前置校验 `media_id` 非空，给出友好错误提示。

### #10 get_article_detail 返回 HTML 未处理
- **文件**: `app/agent/llm_agent.py`
- **问题**: 微信图文正文是 HTML，直接拼进纯文本回复，用户看到满屏 `<p><img>` 标签。
- **修复方向**: 用正则或 html.parser 提取纯文本再输出。

### #11 push_message 未校验内容长度
- **文件**: `app/agent/llm_agent.py`
- **问题**: 未校验 content 长度，超过微信 2048 字限制时直接发送必然失败。
- **修复方向**: 前置截断或分段处理。

### #12 list_published_articles 函数内重复导入 datetime
- **文件**: `app/agent/llm_agent.py` 约第 269 行
- **问题**: `from datetime import datetime` 在函数体内，而文件顶部已有 `from datetime import datetime`。
- **修复方向**: 删除函数内的重复导入。

---

## 🟢 低危

### #13 临时文件无 finally 清理
- **文件**: `app/visit_image_api.py`
- **问题**: 上传失败时 `file_path.unlink()` 不会执行，临时文件泄漏。
- **修复方向**: 改用 `try/finally` 或 `contextlib.ExitStack`。

### #14 session_store JSON 损坏日志不足
- **文件**: `app/agent/session_store.py`
- **问题**: JSON 损坏时静默返回 `[]`，生产环境无法事后审计。
- **修复方向**: 补充更详细的错误日志（包含 openid、数据长度等）。

### #15 wechat_api/client 未检查 HTTP status code
- **文件**: `app/wechat_api/client.py`
- **问题**: 微信返回 HTTP 500 时 `resp.json()` 直接抛异常，未分离 HTTP 错误与业务错误。
- **修复方向**: 加 `resp.raise_for_status()` 或检查 status_code。

### #16 get_wechat_qr_code 不验证 media_id 是否存在于素材库
- **文件**: `app/agent/llm_agent.py`
- **问题**: 只校验配置非空，不验证 media_id 是否真实有效，push_image 可能失败。
- **修复方向**: 配置加载时做一次验证，或文档明确说明配置责任。

### #17 session_db_path 硬编码 /data/
- **文件**: `app/config.py`
- **问题**: `session_db_path: str = "/data/sessions.db"` 不支持多环境部署，本地开发需要手动创建目录。
- **修复方向**: 改为相对路径默认值或从环境变量读取。

### #18 media_index.json 路径硬编码 /data/
- **文件**: `app/media_index.py`
- **问题**: 测试环境和生产环境共享同一个 `/data/media_index.json`，存在数据污染风险。
- **修复方向**: 路径通过 config/环境变量注入。

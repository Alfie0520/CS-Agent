# 微信服务号 API 文档索引

本目录收录了开发**微信服务号客服 Agent** 所需的核心接口文档，所有内容来自微信官方开发者文档。

> 官方文档入口：https://developers.weixin.qq.com/doc/service/guide/dev/api/

---

## 文档地图

```
消息进来（用户 → 服务号）
│
├── 接收普通消息        → service-capability-receive-standard-msg.md
├── 接收事件推送        → service-capability-receive-event-push.md
│
↓ Agent 处理
│
├── 被动回复（5秒内）   → service-capability-passive-reply.md
├── 客服消息（异步）    → service-capability-customer-msg.md
├── 转发人工客服        → service-capability-transfer-to-kf.md
│
└── 辅助能力
    ├── 用户身份识别     → service-capability-user-management.md
    ├── Access Token 管理 → service-guide-dev-api-overview.md
    ├── 消息加解密       → service-guide-msg-encryption.md
    └── 快速入门         → service-guide-dev-start.md
```

---

## 文件说明

### 基础接入

| 文件 | 说明 | 必读 |
|---|---|---|
| `service-guide-dev-start.md` | 快速入门：服务器配置、Token 验证、收发消息完整示例 | ★★★ |
| `service-guide-dev-api-overview.md` | 服务端 API 调用说明 + 获取 Access Token 接口详情 | ★★★ |
| `service-guide-msg-encryption.md` | 消息加解密原理与代码实现（AES-256-CBC） | ★★ |

### 消息收发（Webhook 侧）

> 这类接口是微信**主动推送**给你的服务器，不需要你主动调用，只需要处理 POST 请求。

| 文件 | 说明 | 触发时机 |
|---|---|---|
| `service-capability-receive-standard-msg.md` | 接收用户发来的普通消息（文本/图片/语音/视频/位置/链接） | 用户在对话框发消息 |
| `service-capability-receive-event-push.md` | 接收事件推送（关注/取关/扫码/位置/菜单点击） | 用户产生交互行为 |

### 消息回复（API 调用侧）

> 这类接口是你**主动调用**微信 API 来发消息给用户。

| 文件 | 说明 | 适用场景 |
|---|---|---|
| `service-capability-passive-reply.md` | 被动回复：收到消息后在 5 秒内同步回复 XML | 简单快速回复 |
| `service-capability-customer-msg.md` | 客服消息：异步发送，支持文本/图片/菜单/小程序卡片等 | Agent 主要回复方式 |
| `service-capability-transfer-to-kf.md` | 将会话转交给人工客服 | 需要人工介入时 |

### 用户信息

| 文件 | 说明 |
|---|---|
| `service-capability-user-management.md` | 获取用户 OpenID、基本信息、关注列表；设置备注名 |

---

## 快速查阅指南

### 场景一：刚开始接入，不知道从哪看

先读 `service-guide-dev-start.md`，跟着走一遍完整流程（配置服务器 → 收消息 → 回消息）。

### 场景二：用户发消息后，我该收到什么格式的数据？

查 `service-capability-receive-standard-msg.md`，里面列出了所有消息类型的 XML 字段说明：

- 用户发文字 → `MsgType=text`，读 `Content` 字段
- 用户发图片 → `MsgType=image`，读 `PicUrl` 和 `MediaId`
- 用户发语音 → `MsgType=voice`，读 `MediaId` 和 `Format`

### 场景三：用户关注/取关/点菜单，我能收到通知吗？

查 `service-capability-receive-event-push.md`，所有事件类型的 XML 格式都在里面：

- 关注 → `Event=subscribe`
- 取关 → `Event=unsubscribe`
- 点菜单 → `Event=CLICK`，读 `EventKey` 知道点了哪个按钮

### 场景四：我怎么发消息给用户？

两种方式，按需选择：

| 方式 | 文件 | 限制 |
|---|---|---|
| 被动回复（同步） | `service-capability-passive-reply.md` | 必须在用户发消息后 5 秒内回复；只能回复一条 |
| 客服消息（异步） | `service-capability-customer-msg.md` | 用户发消息后 48 小时内可发；可发多条；支持更多类型 |

**客服 Agent 推荐流程**：收到用户消息后，先回复空串（避免超时），再异步调用客服消息接口发送 AI 处理后的结果。

### 场景五：AI 无法处理，需要转人工怎么做？

查 `service-capability-transfer-to-kf.md`，核心是被动回复一条特殊消息：

```xml
<MsgType><![CDATA[transfer_customer_service]]></MsgType>
```

### 场景六：我想知道是谁发来的消息（用户画像）

查 `service-capability-user-management.md`，用 OpenID 调用接口获取用户信息（关注时间、来源渠道、标签等）。

### 场景七：Access Token 怎么管理？

查 `service-guide-dev-api-overview.md`，关键结论：

- 有效期 **2 小时**，提前刷新
- 用**中控服务器**统一管理，不要多个进程各自刷新
- 推荐存 Redis/MySQL，内存缓存 1 分钟

### 场景八：要不要开消息加密？

查 `service-guide-msg-encryption.md`。
- 开发调试阶段用明文模式
- 上线后建议开启安全模式（AES-256-CBC）
- 注意：通过客服 API 主动发送的消息**不受加密影响**

---

## 接口速查表

| 操作 | 方法 | 路径 |
|---|---|---|
| 获取 Access Token | GET | `/cgi-bin/token` |
| 发送客服消息 | POST | `/cgi-bin/message/custom/send` |
| 获取用户基本信息 | GET | `/cgi-bin/user/info` |
| 批量获取用户信息 | POST | `/cgi-bin/user/info/batchget` |
| 获取关注用户列表 | GET | `/cgi-bin/user/get` |
| 设置用户备注名 | POST | `/cgi-bin/user/info/updateremark` |
| 创建客服会话 | POST | `/customservice/kfsession/create` |
| 关闭客服会话 | POST | `/customservice/kfsession/close` |
| 获取在线客服列表 | GET | `/cgi-bin/customservice/getonlinekflist` |

> 所有接口的 Base URL 为：`https://api.weixin.qq.com`

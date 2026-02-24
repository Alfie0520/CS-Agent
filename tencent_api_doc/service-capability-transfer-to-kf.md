# 将消息转发到客服

> 来源：https://developers.weixin.qq.com/doc/service/guide/capability/customer-service/transfer

本文档介绍如何将用户消息转发给人工客服处理，是客服 Agent 中"人工接管"功能的核心机制。

---

## 介绍

当 AI 客服无法处理用户问题时（如复杂投诉、情绪激动的用户等），需要将用户转接给人工客服。

微信提供了两种转发方式：

1. **被动回复转发**：在回复用户消息时，用 `transfer_customer_service` 类型消息将会话转移给客服
2. **多客服系统**：通过客服会话管理接口，主动创建和管理客服会话

---

## 方式一：被动回复转发（推荐）

在收到用户消息后，通过被动回复接口回复 `MsgType=transfer_customer_service`，将用户消息转发给客服。

### 转发给任意在线客服

```xml
<xml>
  <ToUserName><![CDATA[touser/openid]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1399197672</CreateTime>
  <MsgType><![CDATA[transfer_customer_service]]></MsgType>
</xml>
```

### 转发给指定客服

```xml
<xml>
  <ToUserName><![CDATA[touser/openid]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1399197672</CreateTime>
  <MsgType><![CDATA[transfer_customer_service]]></MsgType>
  <TransInfo>
    <KfAccount><![CDATA[test1@test]]></KfAccount>
  </TransInfo>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | 固定值 `transfer_customer_service` |
| TransInfo.KfAccount | 指定客服账号（格式：账号前缀@公众号微信号），不填则转给任意在线客服 |

---

## 方式二：客服会话管理接口

通过 API 主动创建和管理客服会话。

### 创建会话

```bash
POST https://api.weixin.qq.com/customservice/kfsession/create?access_token=ACCESS_TOKEN
```

```json
{
    "kf_account": "test1@test",
    "openid": "OPENID"
}
```

> 注意：指定的客服账号必须已绑定微信号且在线。

### 关闭会话

```bash
POST https://api.weixin.qq.com/customservice/kfsession/close?access_token=ACCESS_TOKEN
```

```json
{
    "kf_account": "test1@test",
    "openid": "OPENID"
}
```

### 获取客户会话状态

```bash
GET https://api.weixin.qq.com/customservice/kfsession/getsession?access_token=ACCESS_TOKEN&openid=OPENID
```

### 获取未接入会话列表

```bash
GET https://api.weixin.qq.com/customservice/kfsession/getwaitcase?access_token=ACCESS_TOKEN
```

---

## 客服 Agent 推荐转发流程

```
用户消息 → AI 客服判断是否需要人工介入
         ↓ 需要人工介入
  回复 transfer_customer_service XML
         ↓
  微信将后续消息路由给在线客服
         ↓
  人工客服处理（通过微信公众平台客服界面或第三方客服系统）
         ↓
  会话结束后，可继续由 AI 处理
```

---

## 注意事项

1. 转发到客服后，用户后续的消息不再推送到开发者服务器，而是在微信多客服系统中显示。
2. 若客服离线或无可用客服，用户会收到"暂无人工客服在线"的提示。
3. 建议在转发前先通过"获取在线客服列表"接口确认有客服在线。

### 获取在线客服列表

```bash
GET https://api.weixin.qq.com/cgi-bin/customservice/getonlinekflist?access_token=ACCESS_TOKEN
```

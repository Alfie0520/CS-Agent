# 接收事件推送

> 来源：https://developers.weixin.qq.com/doc/service/guide/capability/basic-message/receive-event

在微信用户和服务号发生交互后，微信服务器会以 **POST XML 数据包**的形式推送事件到开发者填写的服务器 URL。

所有事件推送的 `MsgType` 均为 `event`，通过 `Event` 字段区分具体事件类型。

---

## 公共字段

| 参数 | 描述 |
| --- | --- |
| ToUserName | 开发者微信号 |
| FromUserName | 发送方账号（OpenID） |
| CreateTime | 消息创建时间（整型时间戳） |
| MsgType | 消息类型，事件为 `event` |
| Event | 事件类型（见下方各事件） |

---

## 事件类型

### 1. 关注/取消关注事件

用户关注或取消关注服务号时触发。

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[FromUser]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[subscribe]]></Event>
</xml>
```

| Event 值 | 说明 |
| --- | --- |
| `subscribe` | 关注 |
| `unsubscribe` | 取消关注 |

> 取消关注时，开发者无需（也无法）回复此事件。

---

### 2. 扫描带参数二维码事件

用户扫描带场景值二维码时触发，分两种情况：

**情况一：用户未关注时，扫码后触发关注，并推送此事件**

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[FromUser]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[subscribe]]></Event>
  <EventKey><![CDATA[qrscene_123456]]></EventKey>
  <Ticket><![CDATA[TICKET]]></Ticket>
</xml>
```

**情况二：用户已关注时，扫码后推送此事件**

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[FromUser]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[SCAN]]></Event>
  <EventKey><![CDATA[SCENE_VALUE]]></EventKey>
  <Ticket><![CDATA[TICKET]]></Ticket>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| Event | 关注时为 `subscribe`，已关注时为 `SCAN` |
| EventKey | 未关注时为 `qrscene_` 为前缀，已关注时为场景值 ID |
| Ticket | 二维码的 ticket，可用来换取二维码图片 |

---

### 3. 上报地理位置事件

用户同意上报地理位置后，每次进入服务号会话时上报地理位置，或在进入会话后每 5 秒上报一次。

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[LOCATION]]></Event>
  <Latitude>23.137466</Latitude>
  <Longitude>113.352425</Longitude>
  <Precision>119.385040</Precision>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| Event | `LOCATION` |
| Latitude | 地理位置纬度 |
| Longitude | 地理位置经度 |
| Precision | 地理位置精度 |

---

### 4. 自定义菜单事件

用户点击自定义菜单后会触发以下事件（仅适用于 click 类型按钮）：

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[FromUser]]></FromUserName>
  <CreateTime>123456789</CreateTime>
  <MsgType><![CDATA[event]]></MsgType>
  <Event><![CDATA[CLICK]]></Event>
  <EventKey><![CDATA[EVENTKEY]]></EventKey>
</xml>
```

| Event 值 | 说明 |
| --- | --- |
| `CLICK` | 点击菜单拉取消息 |
| `VIEW` | 点击菜单跳转链接 |

| 参数 | 描述 |
| --- | --- |
| EventKey | CLICK 为开发者定义的菜单 key 值；VIEW 为菜单跳转链接 URL |

---

## 注意事项

- 关注/取消关注、扫描带参数二维码等事件是客服 Agent 的重要触发点，可在用户关注时发送欢迎语。
- 推荐在收到 `subscribe` 事件时，主动调用客服消息接口向用户发送欢迎消息。

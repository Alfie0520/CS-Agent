# 接收普通消息

> 来源：https://developers.weixin.qq.com/doc/service/guide/capability/basic-message/receive-message

当普通微信用户向公众账号发消息时，微信服务器将 **POST** 消息的 XML 数据包到开发者填写的服务器 URL 上。

---

## 注意事项

1. 如需在 5 秒内立即回应，使用"被动回复消息"接口；若处理时间较长，可直接回复空串（微信不会重试）。
2. 微信服务器在五秒内收不到响应会断掉连接，并重新发起请求，**总共重试三次**。
3. 关于重试的消息排重，推荐使用 `msgid` 排重。
4. 开启加密后，用户发来的消息和开发者回复的消息都会被加密（通过客服接口 API 发送的消息不受影响）。

---

## 消息类型与 XML 结构

### 文本消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1348831860</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[this is a test]]></Content>
  <MsgId>1234567890123456</MsgId>
  <MsgDataId>xxxx</MsgDataId>
  <Idx>xxxx</Idx>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| ToUserName | 开发者微信号 |
| FromUserName | 发送方账号（OpenID） |
| CreateTime | 消息创建时间（整型时间戳） |
| MsgType | 消息类型，文本为 `text` |
| Content | 文本消息内容 |
| MsgId | 消息 id，64 位整型 |
| MsgDataId | 消息的数据 ID（消息来自文章时才有） |
| Idx | 多图文时第几篇文章，从 1 开始（消息来自文章时才有） |

---

### 图片消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1348831860</CreateTime>
  <MsgType><![CDATA[image]]></MsgType>
  <PicUrl><![CDATA[this is a url]]></PicUrl>
  <MediaId><![CDATA[media_id]]></MediaId>
  <MsgId>1234567890123456</MsgId>
  <MsgDataId>xxxx</MsgDataId>
  <Idx>xxxx</Idx>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | 消息类型，图片为 `image` |
| PicUrl | 图片链接（由系统生成） |
| MediaId | 图片消息媒体 id，可调用获取临时素材接口拉取数据 |

---

### 语音消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1357290913</CreateTime>
  <MsgType><![CDATA[voice]]></MsgType>
  <MediaId><![CDATA[media_id]]></MediaId>
  <Format><![CDATA[Format]]></Format>
  <MsgId>1234567890123456</MsgId>
  <MsgDataId>xxxx</MsgDataId>
  <Idx>xxxx</Idx>
  <MediaId16K><![CDATA[media_id_16k]]></MediaId16K>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | 语音为 `voice` |
| MediaId | 语音消息媒体 id，Format 为 amr 时返回 8K 采样率语音 |
| Format | 语音格式，如 amr、speex 等 |
| MediaId16K | 16K 采样率语音消息媒体 id |

---

### 视频消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1357290913</CreateTime>
  <MsgType><![CDATA[video]]></MsgType>
  <MediaId><![CDATA[media_id]]></MediaId>
  <ThumbMediaId><![CDATA[thumb_media_id]]></ThumbMediaId>
  <MsgId>1234567890123456</MsgId>
  <MsgDataId>xxxx</MsgDataId>
  <Idx>xxxx</Idx>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | 视频为 `video` |
| MediaId | 视频消息媒体 id |
| ThumbMediaId | 视频消息缩略图的媒体 id |

---

### 小视频消息

MsgType 为 `shortvideo`，字段同视频消息。

---

### 地理位置消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1351776360</CreateTime>
  <MsgType><![CDATA[location]]></MsgType>
  <Location_X>23.134521</Location_X>
  <Location_Y>113.358803</Location_Y>
  <Scale>20</Scale>
  <Label><![CDATA[位置信息]]></Label>
  <MsgId>1234567890123456</MsgId>
  <MsgDataId>xxxx</MsgDataId>
  <Idx>xxxx</Idx>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | 地理位置为 `location` |
| Location_X | 地理位置纬度 |
| Location_Y | 地理位置经度 |
| Scale | 地图缩放大小 |
| Label | 地理位置信息 |

---

### 链接消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>1351776360</CreateTime>
  <MsgType><![CDATA[link]]></MsgType>
  <Title><![CDATA[公众平台官网链接]]></Title>
  <Description><![CDATA[公众平台官网链接]]></Description>
  <Url><![CDATA[url]]></Url>
  <MsgId>1234567890123456</MsgId>
  <MsgDataId>xxxx</MsgDataId>
  <Idx>xxxx</Idx>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | 链接为 `link` |
| Title | 消息标题 |
| Description | 消息描述 |
| Url | 消息链接 |

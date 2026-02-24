# 被动回复用户消息

> 来源：https://developers.weixin.qq.com/doc/service/guide/capability/basic-message/passive-reply

当用户发送消息给服务号时，微信服务器会向开发者服务器发送 POST 请求，开发者需要在 **5 秒内**以 XML 格式回复。

---

## 注意事项

1. 回复的消息必须在 **5 秒内**返回，超时微信不处理，并向用户提示"该公众号暂时无法提供服务，请稍后再试"。
2. 如需更长时间处理，应先回复空串（`""`），然后通过**客服消息接口**异步发送实际消息。
3. 只有在用户发送消息后才能使用被动回复，不能主动推送（主动推送使用客服消息接口）。
4. 加密模式下，消息内容需要用 AES 加密后回复。

---

## 回复消息类型

### 1. 回复文本消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>12345678</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[你好]]></Content>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| ToUserName | 接收方账号（用户的 OpenID） |
| FromUserName | 开发者微信号 |
| CreateTime | 消息创建时间（时间戳） |
| MsgType | `text` |
| Content | 回复的文本内容，支持换行（`\n`） |

---

### 2. 回复图片消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>12345678</CreateTime>
  <MsgType><![CDATA[image]]></MsgType>
  <Image>
    <MediaId><![CDATA[media_id]]></MediaId>
  </Image>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | `image` |
| MediaId | 通过素材管理接口上传图片获得的媒体 ID |

---

### 3. 回复语音消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>12345678</CreateTime>
  <MsgType><![CDATA[voice]]></MsgType>
  <Voice>
    <MediaId><![CDATA[media_id]]></MediaId>
  </Voice>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | `voice` |
| MediaId | 通过素材管理接口上传语音获得的媒体 ID |

---

### 4. 回复视频消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>12345678</CreateTime>
  <MsgType><![CDATA[video]]></MsgType>
  <Video>
    <MediaId><![CDATA[media_id]]></MediaId>
    <Title><![CDATA[title]]></Title>
    <Description><![CDATA[description]]></Description>
  </Video>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | `video` |
| MediaId | 通过素材管理接口上传视频获得的媒体 ID |
| Title | 视频标题（可选） |
| Description | 视频描述（可选） |

---

### 5. 回复音乐消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>12345678</CreateTime>
  <MsgType><![CDATA[music]]></MsgType>
  <Music>
    <Title><![CDATA[TITLE]]></Title>
    <Description><![CDATA[DESCRIPTION]]></Description>
    <MusicUrl><![CDATA[MUSIC_URL]]></MusicUrl>
    <HQMusicUrl><![CDATA[HQ_MUSIC_URL]]></HQMusicUrl>
    <ThumbMediaId><![CDATA[media_id]]></ThumbMediaId>
  </Music>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | `music` |
| Title | 音乐标题 |
| Description | 音乐描述 |
| MusicUrl | 音乐链接 |
| HQMusicUrl | 高质量音乐链接，优先使用 |
| ThumbMediaId | 缩略图的媒体 ID，通过素材管理接口上传图片获得 |

---

### 6. 回复图文消息

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <FromUserName><![CDATA[fromUser]]></FromUserName>
  <CreateTime>12345678</CreateTime>
  <MsgType><![CDATA[news]]></MsgType>
  <ArticleCount>1</ArticleCount>
  <Articles>
    <item>
      <Title><![CDATA[title1]]></Title>
      <Description><![CDATA[description1]]></Description>
      <PicUrl><![CDATA[picurl]]></PicUrl>
      <Url><![CDATA[url]]></Url>
    </item>
  </Articles>
</xml>
```

| 参数 | 描述 |
| --- | --- |
| MsgType | `news` |
| ArticleCount | 图文消息个数，限制为 1 条以内 |
| Articles | 多条图文消息信息（item 列表） |
| Title | 图文消息标题 |
| Description | 图文消息描述 |
| PicUrl | 图片链接，支持 JPG、PNG，较好效果为大图 360×200，小图 200×200 |
| Url | 点击图文消息跳转链接 |

---

## 客服 Agent 推荐模式

对于客服 Agent 来说，推荐**先回复空串**，然后通过**客服消息接口**异步发送结果：

```
用户消息 → 开发者服务器收到
         → 立即回复空串（"success" 或 ""）
         → 异步调用 LLM 处理消息
         → 通过客服消息接口 POST 回复给用户
```

这样可以：
- 避免 5 秒超时
- 支持流式处理或多条消息回复
- 完全控制回复时机

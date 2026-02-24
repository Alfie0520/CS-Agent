# 客服消息（发送客服消息）

> 来源：https://developers.weixin.qq.com/doc/service/api/customer/message/api_sendcustommessage

接口英文名：`sendCustomMessage`

本接口用于发送多种类型的客服消息，主要应用在有人工消息处理环节的场景。

当用户和应用产生特定动作的交互时，微信将会把消息数据推送给开发者，开发者可以在一段时间内（目前为 **48 小时**）调用客服接口，通过 POST 一个 JSON 数据包来发送消息给普通用户。

---

## 允许触发客服接口的动作

1. 扫描二维码
2. 关注公众号
3. 点击自定义菜单（仅有"点击推事件"、"扫码推事件"、"扫码推事件且弹出消息接收中"这 3 种菜单类型可触发）
4. **用户发送信息**（最常用）

### 各场景下发额度

| 场景 | 下发额度 | 额度有效期 |
| --- | --- | --- |
| 用户发送消息 | 5 条 | 48 小时 |
| 点击自定义菜单 | 3 条 | 1 分钟 |
| 关注公众号 | 3 条 | 1 分钟 |
| 扫描二维码 | 3 条 | 1 分钟 |

---

## 调用方式

```bash
POST https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=ACCESS_TOKEN
```

---

## 请求参数

### 公共参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| touser | string | 是 | 用户的 OpenID |
| msgtype | string | 是 | 消息类型 |
| customservice | object | 否 | 以某个客服账号来发消息 |

### msgtype 支持的消息类型

| msgtype 值 | 说明 |
| --- | --- |
| `text` | 文本消息 |
| `image` | 图片消息 |
| `voice` | 语音消息 |
| `video` | 视频消息 |
| `music` | 音乐消息 |
| `news` | 图文消息（跳转外链） |
| `mpnewsarticle` | 图文消息（跳转到图文页面） |
| `msgmenu` | 菜单消息 |
| `wxcard` | 卡券 |
| `miniprogrampage` | 小程序卡片 |

---

## 代码示例

### 发送文本消息

```json
{
    "touser": "OPENID",
    "msgtype": "text",
    "text": {
        "content": "您好，请问有什么可以帮助您？"
    }
}
```

支持插入跳小程序的文字链：

```json
{
    "touser": "OPENID",
    "msgtype": "text",
    "text": {
        "content": "点击查看详情 <a href=\"http://www.qq.com\" data-miniprogram-appid=\"appid\" data-miniprogram-path=\"pages/index/index\">跳小程序</a>"
    }
}
```

### 发送图片消息

```json
{
    "touser": "OPENID",
    "msgtype": "image",
    "image": {
        "media_id": "MEDIA_ID"
    }
}
```

### 发送菜单消息（用于交互选择）

```json
{
    "touser": "OPENID",
    "msgtype": "msgmenu",
    "msgmenu": {
        "head_content": "您对本次服务是否满意？",
        "list": [
            { "id": "101", "content": "满意" },
            { "id": "102", "content": "不满意" }
        ],
        "tail_content": "欢迎再次光临"
    }
}
```

### 发送小程序卡片

```json
{
    "touser": "OPENID",
    "msgtype": "miniprogrampage",
    "miniprogrampage": {
        "title": "产品标题",
        "appid": "APPID",
        "pagepath": "pages/index/index",
        "thumb_media_id": "THUMB_MEDIA_ID"
    }
}
```

### 指定客服账号发送

```json
{
    "touser": "OPENID",
    "msgtype": "text",
    "text": {
        "content": "您好！"
    },
    "customservice": {
        "kf_account": "test1@kftest"
    }
}
```

### AI 标识（可选）

```json
{
    "touser": "OPENID",
    "msgtype": "text",
    "text": {
        "content": "根据您的问题..."
    },
    "aimsgcontext": {
        "is_ai_msg": 1
    }
}
```

> 设置 `is_ai_msg: 1` 后，消息下方会显示灰色 wording "内容由第三方 AI 生成"。

---

## 返回参数

```json
{
    "errcode": 0,
    "errmsg": "ok"
}
```

---

## 错误码

| 错误码 | 错误描述 | 解决方案 |
| --- | --- | --- |
| -1 | system error | 系统繁忙，稍候再试 |
| 40001 | invalid credential | access_token 无效 |
| 40013 | invalid appid | AppID 无效 |
| 70000 | 为保护未成年人权益，该条消息发送失败 | — |

---

## 适用范围

| 服务号 |
| --- |
| 仅认证（企业主体已认证） |

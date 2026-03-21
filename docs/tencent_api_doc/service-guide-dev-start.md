# 微信服务号开发者快速入门

> 来源：https://developers.weixin.qq.com/doc/service/guide/dev/start.html

公众平台技术文档的目的是为了简明扼要的说明接口的使用。本文面向刚入门的开发者，旨在帮助大家入门微信开放平台的开发者模式。

---

## 目录

1. [环境准备](#1-环境准备)
2. [实现"你问我答"（文本消息收发）](#2-实现你问我答)
3. [实现"图尚往来"（图片消息收发）](#3-实现图尚往来)
4. [AccessToken](#4-accesstoken)
5. [临时素材](#5-临时素材)
6. [永久素材](#6-永久素材)
7. [自定义菜单](#7-自定义菜单)

---

## 1 环境准备

### 1.1 申请服务器

以腾讯云服务器为示例：[腾讯云服务器购买入口](https://buy.qcloud.com/cvm?cpu=1&mem=1)

如已有小程序并开通云开发，可使用[服务号环境共享](https://developers.weixin.qq.com/miniprogram/dev/wxcloud/basis/web.html)能力。

### 1.2 搭建服务

以 web.py + Python + 腾讯云服务器为例：

**安装依赖：**
- Python 2.7+
- web.py
- libxml2, libxslt, lxml

**main.py 初始版本：**

```python
# -*- coding: utf-8 -*-
# filename: main.py
import web

urls = (
    '/wx', 'Handle',
)

class Handle(object):
    def GET(self):
        return "hello, this is handle view"

if __name__ == '__main__':
    app = web.application(urls, globals())
    app.run()
```

启动命令：`sudo python main.py 80`

URL 填写：`http://外网IP/wx`

### 1.3 注册服务号

- [点此注册服务号](https://mp.weixin.qq.com/cgi-bin/readtemplate?t=register/step1_tmpl&lang=zh_CN&service=1&token=)

### 1.4 开发者基本配置

前往「微信开发者平台 - 我的业务与服务 - 服务号 - 开发信息」进行配置，填写服务器地址（URL）、Token 等信息。

**handle.py（Token 验证）：**

```python
# -*- coding: utf-8 -*-
# filename: handle.py
import hashlib
import web

class Handle(object):
    def GET(self):
        try:
            data = web.input()
            if len(data) == 0:
                return "hello, this is handle view"
            signature = data.signature
            timestamp = data.timestamp
            nonce = data.nonce
            echostr = data.echostr
            token = "xxxx"  # 请按照公众平台官网基本配置中信息填写

            list = [token, timestamp, nonce]
            list.sort()
            sha1 = hashlib.sha1()
            map(sha1.update, list)
            hashcode = sha1.hexdigest()
            if hashcode == signature:
                return echostr
            else:
                return ""
        except Exception, Argument:
            return Argument
```

### 1.5 推荐的生产架构

安全稳定高效的服务号建议采用三层结构：

| 模块 | 职责 |
|------|------|
| **业务逻辑服务器** | 处理具体业务 |
| **API-Proxy 服务器** | 专一对接微信 API，控制调用频率和权限 |
| **AccessToken 中控服务器** | 统一管理 access_token 的获取与刷新，防止并发覆盖 |

---

## 2 实现"你问我答"

**目标：** 粉丝发文本消息 → 服务号自动回复文本消息

### 2.1 接收文本消息

粉丝发送文本消息时，微信后台推送给开发者的 XML 格式：

```xml
<xml>
  <ToUserName><![CDATA[服务号]]></ToUserName>
  <FromUserName><![CDATA[粉丝号]]></FromUserName>
  <CreateTime>1460537339</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[欢迎开启服务号开发者模式]]></Content>
  <MsgId>6272960105994287618</MsgId>
</xml>
```

字段说明：
- `CreateTime`：消息发送时间戳
- `MsgType`：消息类型（text/image/voice 等）
- `Content`：消息内容
- `MsgId`：消息唯一标识

### 2.2 被动回复文本消息

开发者回复给微信后台的 XML 格式：

```xml
<xml>
  <ToUserName><![CDATA[粉丝号]]></ToUserName>
  <FromUserName><![CDATA[服务号]]></FromUserName>
  <CreateTime>1460541339</CreateTime>
  <MsgType><![CDATA[text]]></MsgType>
  <Content><![CDATA[test]]></Content>
</xml>
```

### 2.3 回复 success 说明

> 若服务器无法在 **5 秒内**处理并回复，必须返回 `"success"` 或空字符串，否则微信后台会发起 **3 次重试**，最终在用户界面显示错误提示。

### 2.4 完整代码实现

**handle.py：**

```python
# -*- coding: utf-8 -*-
# filename: handle.py
import hashlib
import reply
import receive
import web

class Handle(object):
    def POST(self):
        try:
            webData = web.data()
            recMsg = receive.parse_xml(webData)
            if isinstance(recMsg, receive.Msg) and recMsg.MsgType == 'text':
                toUser = recMsg.FromUserName
                fromUser = recMsg.ToUserName
                content = "test"
                replyMsg = reply.TextMsg(toUser, fromUser, content)
                return replyMsg.send()
            else:
                return "success"
        except Exception, Argment:
            return Argment
```

**receive.py：**

```python
# -*- coding: utf-8 -*-
# filename: receive.py
import xml.etree.ElementTree as ET

def parse_xml(web_data):
    if len(web_data) == 0:
        return None
    xmlData = ET.fromstring(web_data)
    msg_type = xmlData.find('MsgType').text
    if msg_type == 'text':
        return TextMsg(xmlData)
    elif msg_type == 'image':
        return ImageMsg(xmlData)

class Msg(object):
    def __init__(self, xmlData):
        self.ToUserName = xmlData.find('ToUserName').text
        self.FromUserName = xmlData.find('FromUserName').text
        self.CreateTime = xmlData.find('CreateTime').text
        self.MsgType = xmlData.find('MsgType').text
        self.MsgId = xmlData.find('MsgId').text

class TextMsg(Msg):
    def __init__(self, xmlData):
        Msg.__init__(self, xmlData)
        self.Content = xmlData.find('Content').text.encode("utf-8")

class ImageMsg(Msg):
    def __init__(self, xmlData):
        Msg.__init__(self, xmlData)
        self.PicUrl = xmlData.find('PicUrl').text
        self.MediaId = xmlData.find('MediaId').text
```

**reply.py：**

```python
# -*- coding: utf-8 -*-
# filename: reply.py
import time

class Msg(object):
    def send(self):
        return "success"

class TextMsg(Msg):
    def __init__(self, toUserName, fromUserName, content):
        self.__dict = dict()
        self.__dict['ToUserName'] = toUserName
        self.__dict['FromUserName'] = fromUserName
        self.__dict['CreateTime'] = int(time.time())
        self.__dict['Content'] = content

    def send(self):
        XmlForm = """
            <xml>
                <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
                <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
                <CreateTime>{CreateTime}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{Content}]]></Content>
            </xml>
            """
        return XmlForm.format(**self.__dict)

class ImageMsg(Msg):
    def __init__(self, toUserName, fromUserName, mediaId):
        self.__dict = dict()
        self.__dict['ToUserName'] = toUserName
        self.__dict['FromUserName'] = fromUserName
        self.__dict['CreateTime'] = int(time.time())
        self.__dict['MediaId'] = mediaId

    def send(self):
        XmlForm = """
            <xml>
                <ToUserName><![CDATA[{ToUserName}]]></ToUserName>
                <FromUserName><![CDATA[{FromUserName}]]></FromUserName>
                <CreateTime>{CreateTime}</CreateTime>
                <MsgType><![CDATA[image]]></MsgType>
                <Image>
                    <MediaId><![CDATA[{MediaId}]]></MediaId>
                </Image>
            </xml>
            """
        return XmlForm.format(**self.__dict)
```

---

## 3 实现"图尚往来"

**目标：** 粉丝发图片消息 → 服务号回复相同图片

### 3.1 接收图片消息

```xml
<xml>
  <ToUserName><![CDATA[服务号]]></ToUserName>
  <FromUserName><![CDATA[粉丝号]]></FromUserName>
  <CreateTime>1460536575</CreateTime>
  <MsgType><![CDATA[image]]></MsgType>
  <PicUrl><![CDATA[http://mmbiz.qpic.cn/xxxxxx/0]]></PicUrl>
  <MsgId>6272956824639273066</MsgId>
  <MediaId><![CDATA[gyci5a-xxxxx-OL]]></MediaId>
</xml>
```

字段说明：
- `PicUrl`：图片 URL（可直接用浏览器查看）
- `MediaId`：微信系统生成的素材 ID，用于后续调用

### 3.2 被动回复图片消息

```xml
<xml>
  <ToUserName><![CDATA[粉丝号]]></ToUserName>
  <FromUserName><![CDATA[服务号]]></FromUserName>
  <CreateTime>1460536576</CreateTime>
  <MsgType><![CDATA[image]]></MsgType>
  <Image>
    <MediaId><![CDATA[gyci5oxxxxxxv3cOL]]></MediaId>
  </Image>
</xml>
```

### 3.3 handle.py 更新（同时处理文本和图片）

```python
# -*- coding: utf-8 -*-
# filename: handle.py
import reply
import receive
import web

class Handle(object):
    def POST(self):
        try:
            webData = web.data()
            recMsg = receive.parse_xml(webData)
            if isinstance(recMsg, receive.Msg):
                toUser = recMsg.FromUserName
                fromUser = recMsg.ToUserName
                if recMsg.MsgType == 'text':
                    content = "test"
                    replyMsg = reply.TextMsg(toUser, fromUser, content)
                    return replyMsg.send()
                if recMsg.MsgType == 'image':
                    mediaId = recMsg.MediaId
                    replyMsg = reply.ImageMsg(toUser, fromUser, mediaId)
                    return replyMsg.send()
                else:
                    return reply.Msg().send()
            else:
                return reply.Msg().send()
        except Exception, Argment:
            return Argment
```

---

## 4 AccessToken

> 参考：[Access_token 使用说明](https://developers.weixin.qq.com/doc/oplatform/developers/dev/AccessToken.html)

**注意事项：**
1. 必须使用**中控服务器**统一管理 access_token，不能在各业务模块中分别获取
2. 并发获取会导致 access_token 互相覆盖，影响业务稳定性
3. access_token 有效期为 **7200 秒**，需主动或被动刷新

**basic.py（仅作参考，生产环境请用中控服务器）：**

```python
# -*- coding: utf-8 -*-
# filename: basic.py
import urllib
import time
import json

class Basic:
    def __init__(self):
        self.__accessToken = ''
        self.__leftTime = 0

    def __real_get_access_token(self):
        appId = "xxxxx"       # 替换为实际 AppID
        appSecret = "xxxxx"   # 替换为实际 AppSecret
        postUrl = ("https://api.weixin.qq.com/cgi-bin/token?grant_type="
                   "client_credential&appid=%s&secret=%s" % (appId, appSecret))
        urlResp = urllib.urlopen(postUrl)
        urlResp = json.loads(urlResp.read())
        self.__accessToken = urlResp['access_token']
        self.__leftTime = urlResp['expires_in']

    def get_access_token(self):
        if self.__leftTime < 10:
            self.__real_get_access_token()
        return self.__accessToken

    def run(self):
        while True:
            if self.__leftTime > 10:
                time.sleep(2)
                self.__leftTime -= 2
            else:
                self.__real_get_access_token()
```

---

## 5 临时素材

临时素材用于消息中的多媒体文件，通过 MediaID 引用，**不会长期存储**，公众平台后台无法查询。

### 5.1 上传临时素材

接口文档：[新增临时素材](https://developers.weixin.qq.com/doc/service/api/material/temporary/api_uploadtempmedia.html)

```python
# -*- coding: utf-8 -*-
# filename: media.py
from basic import Basic
import urllib2
import poster.encode
from poster.streaminghttp import register_openers

class Media(object):
    def __init__(self):
        register_openers()

    def upload(self, accessToken, filePath, mediaType):
        openFile = open(filePath, "rb")
        param = {'media': openFile}
        postData, postHeaders = poster.encode.multipart_encode(param)
        postUrl = "https://api.weixin.qq.com/cgi-bin/media/upload?access_token=%s&type=%s" % (
            accessToken, mediaType)
        request = urllib2.Request(postUrl, postData, postHeaders)
        urlResp = urllib2.urlopen(request)
        print urlResp.read()

if __name__ == '__main__':
    myMedia = Media()
    accessToken = Basic().get_access_token()
    filePath = "/path/to/test.jpg"  # 替换为实际路径
    mediaType = "image"
    myMedia.upload(accessToken, filePath, mediaType)
```

### 5.2 获取临时素材 MediaID 的两种方式

1. 上传接口调用成功后，从返回 JSON 中提取 `media_id`
2. 粉丝互动时，从推送的 XML 数据中提取 `MediaId`

### 5.3 下载临时素材

接口文档：[获取临时素材](https://developers.weixin.qq.com/doc/service/api/material/temporary/api_getmedia.html)

浏览器直接访问（替换参数）：
```
https://api.weixin.qq.com/cgi-bin/media/get?access_token=ACCESS_TOKEN&media_id=MEDIA_ID
```

代码实现：

```python
class Media(object):
    def get(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/media/get?access_token=%s&media_id=%s" % (
            accessToken, mediaId)
        urlResp = urllib2.urlopen(postUrl)
        headers = urlResp.info().__dict__['headers']
        if ('Content-Type: application/json\r\n' in headers) or ('Content-Type: text/plain\r\n' in headers):
            jsonDict = json.loads(urlResp.read())
            print jsonDict
        else:
            buffer = urlResp.read()
            mediaFile = file("test_media.jpg", "wb")
            mediaFile.write(buffer)
            print "get successful"
```

---

## 6 永久素材

永久素材长期保存，数量有上限，可在公众平台后台素材管理中查看。

### 6.1 新增永久素材

以图文素材为例：

```python
# -*- coding: utf-8 -*-
# filename: material.py
import urllib2
import json
from basic import Basic

class Material(object):
    def add_news(self, accessToken, news):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/add_news?access_token=%s" % accessToken
        urlResp = urllib2.urlopen(postUrl, news)
        print urlResp.read()

if __name__ == '__main__':
    myMaterial = Material()
    accessToken = Basic().get_access_token()
    news = {
        "articles": [{
            "title": "test",
            "thumb_media_id": "替换为实际thumb_media_id",
            "author": "作者名",
            "digest": "",
            "show_cover_pic": 1,
            "content": "<p>内容</p>",
            "content_source_url": "",
        }]
    }
    news = json.dumps(news, ensure_ascii=False)
    myMaterial.add_news(accessToken, news)
```

### 6.2 获取永久素材 MediaID

1. 新增素材时保存返回的 `media_id`
2. 调用素材列表接口批量拉取

### 6.3 素材列表 / 上传 / 下载 / 删除

```python
class Material(object):
    # 上传
    def upload(self, accessToken, filePath, mediaType):
        # ...（使用 poster 库 multipart 上传）
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=%s&type=%s" % (accessToken, mediaType)

    # 下载
    def get(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/get_material?access_token=%s" % accessToken
        postData = '{ "media_id": "%s" }' % mediaId

    # 删除
    def delete(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/del_material?access_token=%s" % accessToken
        postData = '{ "media_id": "%s" }' % mediaId

    # 获取列表
    def batch_get(self, accessToken, mediaType, offset=0, count=20):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token=%s" % accessToken
        postData = '{ "type": "%s", "offset": %d, "count": %d }' % (mediaType, offset, count)
```

相关接口文档：
- [新增永久素材](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html)
- [获取永久素材列表](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_batchgetmaterial.html)
- [删除永久素材](https://developers.weixin.qq.com/doc/service/api/material/permanent/api_delmaterial.html)

---

## 7 自定义菜单

支持三种按钮类型：

| 类型 | 说明 |
|------|------|
| `click` | 点击后触发事件推送，开发者可自定义回复 |
| `view` | 跳转到指定 URL |
| `media_id` | 发送指定永久素材 |

### 7.1 创建菜单

接口文档：[创建自定义菜单](https://developers.weixin.qq.com/doc/service/api/custommenu/api_createcustommenu.html)

```python
# -*- coding: utf-8 -*-
# filename: menu.py
import urllib
from basic import Basic

class Menu(object):
    def create(self, postData, accessToken):
        postUrl = "https://api.weixin.qq.com/cgi-bin/menu/create?access_token=%s" % accessToken
        if isinstance(postData, unicode):
            postData = postData.encode('utf-8')
        urlResp = urllib.urlopen(url=postUrl, data=postData)
        print urlResp.read()

    def query(self, accessToken):
        postUrl = "https://api.weixin.qq.com/cgi-bin/menu/get?access_token=%s" % accessToken
        urlResp = urllib.urlopen(url=postUrl)
        print urlResp.read()

    def delete(self, accessToken):
        postUrl = "https://api.weixin.qq.com/cgi-bin/menu/delete?access_token=%s" % accessToken
        urlResp = urllib.urlopen(url=postUrl)
        print urlResp.read()

if __name__ == '__main__':
    myMenu = Menu()
    postJson = """
    {
        "button": [
            { "type": "click", "name": "开发指引", "key": "mpGuide" },
            {
                "name": "公众平台",
                "sub_button": [
                    { "type": "view", "name": "更新公告", "url": "https://mp.weixin.qq.com/..." },
                    { "type": "view", "name": "接口权限说明", "url": "https://mp.weixin.qq.com/..." }
                ]
            },
            { "type": "media_id", "name": "旅行", "media_id": "替换为实际media_id" }
        ]
    }
    """
    accessToken = Basic().get_access_token()
    myMenu.create(postJson, accessToken)
```

### 7.2 处理菜单 click 事件

点击 `click` 类型菜单后，微信会推送 event 类型 XML，需在后台处理：

**receive.py 新增 EventMsg 支持：**

```python
def parse_xml(web_data):
    # ...
    if msg_type == 'event':
        event_type = xmlData.find('Event').text
        if event_type == 'CLICK':
            return Click(xmlData)
    # ...

class EventMsg(object):
    def __init__(self, xmlData):
        self.ToUserName = xmlData.find('ToUserName').text
        self.FromUserName = xmlData.find('FromUserName').text
        self.CreateTime = xmlData.find('CreateTime').text
        self.MsgType = xmlData.find('MsgType').text
        self.Event = xmlData.find('Event').text

class Click(EventMsg):
    def __init__(self, xmlData):
        EventMsg.__init__(self, xmlData)
        self.Eventkey = xmlData.find('EventKey').text
```

**handle.py 新增 click 事件处理：**

```python
if isinstance(recMsg, receive.EventMsg):
    toUser = recMsg.FromUserName
    fromUser = recMsg.ToUserName
    if recMsg.Event == 'CLICK':
        if recMsg.Eventkey == 'mpGuide':
            content = u"编写中，尚未完成".encode('utf-8')
            replyMsg = reply.TextMsg(toUser, fromUser, content)
            return replyMsg.send()
```

---

## 常用 API 速查

| 功能 | 接口地址 |
|------|----------|
| 获取 access_token | `GET https://api.weixin.qq.com/cgi-bin/token` |
| 上传临时素材 | `POST https://api.weixin.qq.com/cgi-bin/media/upload` |
| 下载临时素材 | `GET https://api.weixin.qq.com/cgi-bin/media/get` |
| 上传永久素材 | `POST https://api.weixin.qq.com/cgi-bin/material/add_material` |
| 下载永久素材 | `POST https://api.weixin.qq.com/cgi-bin/material/get_material` |
| 删除永久素材 | `POST https://api.weixin.qq.com/cgi-bin/material/del_material` |
| 获取素材列表 | `POST https://api.weixin.qq.com/cgi-bin/material/batchget_material` |
| 新增图文素材 | `POST https://api.weixin.qq.com/cgi-bin/material/add_news` |
| 创建自定义菜单 | `POST https://api.weixin.qq.com/cgi-bin/menu/create` |
| 查询自定义菜单 | `GET https://api.weixin.qq.com/cgi-bin/menu/get` |
| 删除自定义菜单 | `GET https://api.weixin.qq.com/cgi-bin/menu/delete` |

---

*最后更新：2026-02-24*

# 消息加解密说明

> 来源：https://developers.weixin.qq.com/doc/service/guide/dev/message/encryption

本文档介绍微信服务号消息加解密的完整流程，适用于需要开启消息加密模式的开发者。

---

## 加密模式说明

微信支持以下三种消息加密模式，可在公众平台后台的"开发 → 基本配置 → 消息加密方式"处设置：

| 加密模式 | 说明 |
| --- | --- |
| **明文模式**（默认） | 不加密，消息以明文 XML 格式传输，调试阶段推荐使用 |
| **兼容模式** | 同时发送明文和密文，便于开发者调试过渡 |
| **安全模式（加密模式）** | 只发送密文，生产环境推荐使用 |

---

## 加密算法

采用 **AES-256-CBC** 对称加密算法。

- 密钥（EncodingAESKey）由开发者在公众平台后台随机生成，长度为 43 位字符（Base64 编码，解码后为 32 字节 AES 密钥）
- 初始化向量（IV）为密钥的前 16 字节

---

## 加密消息格式

开启加密后，微信服务器推送给开发者的消息格式如下：

```xml
<xml>
  <ToUserName><![CDATA[toUser]]></ToUserName>
  <Encrypt><![CDATA[msg_encrypt]]></Encrypt>
</xml>
```

同时，POST 请求的 URL 参数中会附加签名信息：

```
?signature=XXX&timestamp=YYY&nonce=ZZZ&msg_signature=WWWW
```

| 参数 | 说明 |
| --- | --- |
| signature | 开发者服务器配置的 Token 计算的签名 |
| timestamp | 时间戳 |
| nonce | 随机数 |
| msg_signature | 消息体签名，用于验证消息完整性 |

---

## 解密流程

### 步骤 1：验证消息签名

将 `token`、`timestamp`、`nonce`、`msg_encrypt` 拼接后进行 SHA1 计算，与 `msg_signature` 对比，验证消息合法性。

```python
import hashlib

def verify_msg_signature(token, timestamp, nonce, msg_encrypt, msg_signature):
    items = sorted([token, timestamp, nonce, msg_encrypt])
    sha1 = hashlib.sha1()
    sha1.update(''.join(items).encode('utf-8'))
    return sha1.hexdigest() == msg_signature
```

### 步骤 2：Base64 解码密文

```python
import base64

encrypt_bytes = base64.b64decode(msg_encrypt)
```

### 步骤 3：AES 解密

```python
from Crypto.Cipher import AES

def decrypt(aes_key, encrypt_bytes):
    aes_key = base64.b64decode(aes_key + '=')  # 补全 Base64 padding
    iv = aes_key[:16]
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(encrypt_bytes)
    # 去除 PKCS7 padding
    pad = decrypted[-1]
    decrypted = decrypted[:-pad]
    return decrypted
```

### 步骤 4：解析解密结果

解密后的明文结构为：

```
random(16 字节) + msg_len(4 字节，网络字节序) + msg(msg_len 字节) + appid
```

```python
import struct

def parse_decrypted(decrypted):
    msg_len = struct.unpack('>I', decrypted[16:20])[0]
    msg_content = decrypted[20:20 + msg_len].decode('utf-8')
    from_appid = decrypted[20 + msg_len:].decode('utf-8')
    return msg_content, from_appid
```

---

## 加密回复流程

当开发者需要向用户发送加密回复时（被动回复接口）：

### 步骤 1：构造明文消息 XML

```xml
<xml>
  <ToUserName>...</ToUserName>
  <FromUserName>...</FromUserName>
  <CreateTime>...</CreateTime>
  <MsgType>text</MsgType>
  <Content>你好</Content>
</xml>
```

### 步骤 2：AES 加密

```python
import os

def encrypt(aes_key, appid, msg_xml):
    aes_key = base64.b64decode(aes_key + '=')
    iv = aes_key[:16]
    random_bytes = os.urandom(16)
    msg_bytes = msg_xml.encode('utf-8')
    msg_len = struct.pack('>I', len(msg_bytes))
    appid_bytes = appid.encode('utf-8')
    plain = random_bytes + msg_len + msg_bytes + appid_bytes
    # PKCS7 padding
    pad_len = 32 - len(plain) % 32
    plain += bytes([pad_len] * pad_len)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(plain)
    return base64.b64encode(encrypted).decode('utf-8')
```

### 步骤 3：计算回复签名

```python
def make_msg_signature(token, timestamp, nonce, msg_encrypt):
    items = sorted([token, timestamp, nonce, msg_encrypt])
    sha1 = hashlib.sha1()
    sha1.update(''.join(items).encode('utf-8'))
    return sha1.hexdigest()
```

### 步骤 4：构造回复 XML

```xml
<xml>
  <Encrypt><![CDATA[msg_encrypt]]></Encrypt>
  <MsgSignature><![CDATA[msg_signature]]></MsgSignature>
  <TimeStamp>timestamp</TimeStamp>
  <Nonce><![CDATA[nonce]]></Nonce>
</xml>
```

---

## 注意事项

1. **EncodingAESKey** 长度固定为 43 位（Base64 编码），解码后为 32 字节 AES 密钥。
2. 兼容模式下，POST 请求体中同时包含 `<Encrypt>` 和明文字段，开发者应优先读取 `<Encrypt>`。
3. 主动调用 API（如客服消息接口）发送的消息**不受消息加密影响**，API 调用始终使用明文 JSON。
4. 微信官方提供多语言 SDK，建议直接使用官方 SDK：[https://developers.weixin.qq.com/doc/oplatform/downloads/Demo_and_Tools.html](https://developers.weixin.qq.com/doc/oplatform/downloads/Demo_and_Tools.html)

# 用户管理

> 来源：https://developers.weixin.qq.com/doc/service/api/usermanage/

本文档介绍服务号用户管理相关接口，包括获取用户基本信息、获取关注用户列表、用户标签管理等。

---

## 目录

1. [获取用户基本信息](#1-获取用户基本信息)
2. [批量获取用户基本信息](#2-批量获取用户基本信息)
3. [获取关注用户列表](#3-获取关注用户列表)
4. [设置用户备注名](#4-设置用户备注名)

---

## 1 获取用户基本信息

> 来源：https://developers.weixin.qq.com/doc/service/api/usermanage/userinfo/api_userinfo

接口英文名：`userInfo`

在关注者与公众号产生消息交互后，公众号可获得关注者的 OpenID，通过本接口根据 OpenID 获取用户基本信息。

### 调用方式

```bash
GET https://api.weixin.qq.com/cgi-bin/user/info?access_token=ACCESS_TOKEN&openid=OPENID&lang=zh_CN
```

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| access_token | string | 是 | 接口调用凭证 |
| openid | string | 是 | 普通用户的标识，对当前公众号唯一 |
| lang | string | 否 | 返回国家地区语言版本（`zh_CN` / `zh_TW` / `en`） |

### 返回参数

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| subscribe | number | 用户是否订阅该公众号（0：未关注，此时拉取不到其余信息） |
| openid | string | 用户标识，对当前公众号唯一 |
| subscribe_time | timestamp | 用户关注时间戳，多次关注取最后关注时间 |
| unionid | string | 绑定微信开放平台后才有此字段，用于跨应用统一用户身份 |
| remark | string | 公众号运营者对粉丝的备注 |
| groupid | number | 用户所在分组 ID |
| tagid_list | array | 用户被打上的标签 ID 列表 |
| subscribe_scene | string | 用户关注来源渠道 |
| qr_scene | number | 二维码扫码场景（开发者自定义） |
| qr_scene_str | string | 二维码扫码场景描述 |

> 注意：2021 年 12 月 27 日之后，不再输出头像、昵称信息。

### subscribe_scene 可能的值

| 值 | 说明 |
| --- | --- |
| `ADD_SCENE_SEARCH` | 公众号搜索 |
| `ADD_SCENE_QR_CODE` | 扫描二维码 |
| `ADD_SCENE_PROFILE_CARD` | 名片分享 |
| `ADD_SCENE_PROFILE_LINK` | 图文页内名称点击 |
| `ADD_SCENE_WECHAT_ADVERTISEMENT` | 微信广告 |
| `ADD_SCENE_WXA` | 小程序关注 |
| `ADD_SCENE_OTHERS` | 其他 |

### 返回示例

```json
{
    "subscribe": 1,
    "openid": "o6_bmjrPTlm6_2sgVt7hMZOPfL2M",
    "subscribe_time": 1382694957,
    "unionid": "o6_bmasdasdsad6_2sgVt7hMZOPfL",
    "remark": "",
    "groupid": 0,
    "tagid_list": [128, 2],
    "subscribe_scene": "ADD_SCENE_QR_CODE",
    "qr_scene": 98765,
    "qr_scene_str": ""
}
```

### 错误码

| 错误码 | 描述 | 解决方案 |
| --- | --- | --- |
| 40003 | invalid openid | 用户未关注或 openid 错误 |
| 40013 | invalid appid | AppID 无效 |

### 适用范围

| 公众号 | 服务号 |
| --- | --- |
| 仅认证 | 仅认证 |

---

## 2 批量获取用户基本信息

> 来源：https://developers.weixin.qq.com/doc/service/api/usermanage/userinfo/api_batchuserinfo

```bash
POST https://api.weixin.qq.com/cgi-bin/user/info/batchget?access_token=ACCESS_TOKEN
```

```json
{
    "user_list": [
        {"openid": "otvxTs4dckWG7imySrJd6jSi0CWE", "lang": "zh_CN"},
        {"openid": "otvxTs_JZ6SEiP0imdhpi50fuSZg", "lang": "zh_CN"}
    ]
}
```

一次请求最多可获取 **100** 条用户信息。

---

## 3 获取关注用户列表

> 来源：https://developers.weixin.qq.com/doc/service/api/usermanage/userinfo/api_getfans

接口英文名：`getFans`

获取账号的关注者 OpenID 列表，一次最多拉取 **10000** 个。

### 调用方式

```bash
GET https://api.weixin.qq.com/cgi-bin/user/get?access_token=ACCESS_TOKEN&next_openid=OPENID
```

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| access_token | string | 是 | 接口调用凭证 |
| next_openid | string | 否 | 上一批列表的最后一个 OPENID，不填默认从头开始拉取 |

### 返回参数

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| total | number | 关注该公众号的总用户数 |
| count | number | 本次拉取的 OPENID 个数 |
| data.openid | array | OPENID 列表 |
| next_openid | string | 下一批拉取的起始 OPENID，为空表示列表结束 |

### 返回示例

```json
{
    "total": 23000,
    "count": 10000,
    "data": {
        "openid": ["OPENID1", "OPENID2", "..."]
    },
    "next_openid": "OPENID10000"
}
```

---

## 4 设置用户备注名

> 来源：https://developers.weixin.qq.com/doc/service/api/usermanage/userinfo/api_updateremark

```bash
POST https://api.weixin.qq.com/cgi-bin/user/info/updateremark?access_token=ACCESS_TOKEN
```

```json
{
    "openid": "oDF3iY9ffA-hqb2vVvbr7qxf6A0Q",
    "remark": "客户名称"
}
```

> 该接口暂时只开放给微信认证的服务号。

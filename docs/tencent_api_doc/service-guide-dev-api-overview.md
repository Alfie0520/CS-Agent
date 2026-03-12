# 服务端 API 调用说明

> 来源：https://developers.weixin.qq.com/doc/service/guide/dev/api/

本文档主要介绍如何调用服务号的 API。

---

## 目录

1. [获取 AppID 和 AppSecret](#1-获取-appid-和-appsecret)
2. [生成 Access Token](#2-生成-access-token)
3. [接口域名](#3-接口域名)
4. [接口限频](#4-接口限频)
5. [获取接口调用凭据（API 详情）](#5-获取接口调用凭据api-详情)

---

## 1 获取 AppID 和 AppSecret

微信开发者平台已支持管理服务号的基本信息、开发信息以及绑定关系和授权关系。

操作路径：「微信开发者平台 - 扫码登录 - 我的业务 - 服务号」，点击后进入服务号管理页面。

开发者可在此处直接修改 AppSecret、API IP 白名单信息、JS 接口安全域名以及消息推送的配置。

### AppSecret 管理

支持启用、重置、冻结以及解冻操作；冻结与解冻操作需 10 分钟后方可生效。

- AppSecret 冻结后，无法使用 AppSecret 获取 Access Token（接口返回错误码 40243）
- 不影响账号基本功能的正常使用
- 不影响通过第三方授权调用后台接口
- 不影响云开发调用后台接口

> 如果 secret 被冻结了调用 getAccessToken 会出现 40243 错误

### IP 白名单

白名单内的 IP 才可以调用获取接口调用凭据接口或获取稳定版接口调用凭据接口，否则会提示 61004 错误。

---

## 2 生成 Access Token

传入 `AppID` 和 `AppSecret` 获取 Access Token，推荐使用稳定版接口。

### 注意事项

1. access_token 有效期为 **2 小时**（7200 秒），需定时刷新，重复获取将导致上次获取的 access_token 失效。
2. 建议使用**中控服务器**统一获取和刷新 access_token，其他业务服务器从该中控服务器获取，不应各自去刷新。
3. 中控服务器需要提供被动刷新 access_token 的接口，便于业务服务器在 API 调用获知 access_token 超时时触发刷新。
4. access_token 的存储至少要保留 512 个字符空间。

### 简单存储方案

1. 中控服务器定时（建议 1 小时）调用微信 API 刷新 access_token，将新的 access_token 存入存储
2. 其他工作服务器每次调用微信 API 时从 MySQL（或其他存储）获取 access_token，可在内存缓存一段时间（建议 1 分钟）

---

## 3 接口域名

| 域名 | 说明 |
| --- | --- |
| `api.weixin.qq.com` | 通用域名，访问官方指定就近接入点 |
| `api2.weixin.qq.com` | 通用异地容灾域名 |
| `sh.api.weixin.qq.com` | 上海域名 |
| `sz.api.weixin.qq.com` | 深圳域名 |
| `hk.api.weixin.qq.com` | 香港域名 |

> 请使用域名进行 API 接口请求，不要使用 IP 访问。

---

## 4 接口限频

为防止程序错误引发微信服务器负载异常，每个服务号调用接口都不能超过一定限制，具体参考接口限频说明。

---

## 5 获取接口调用凭据（API 详情）

> 来源：https://developers.weixin.qq.com/doc/service/api/base/api_getaccesstoken

接口英文名：`getAccessToken`

本接口用于获取全局唯一后台接口调用凭据（Access Token），token 有效期为 7200 秒。

推荐使用 [获取稳定版接口调用凭据](https://developers.weixin.qq.com/doc/service/api/base/api_getstableaccesstoken)。

### 调用方式

```bash
GET https://api.weixin.qq.com/cgi-bin/token
```

### 请求参数

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| grant_type | string | 是 | 填写 `client_credential` |
| appid | string | 是 | 账号的唯一凭证，即 AppID |
| secret | string | 是 | 唯一凭证密钥，即 AppSecret |

### 请求示例

```bash
GET https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=APPID&secret=APPSECRET
```

### 返回参数

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| access_token | string | 获取到的凭证 |
| expires_in | number | 凭证有效时间，单位：秒（目前为 7200 秒） |

### 返回示例

```json
{
  "access_token": "ACCESS_TOKEN",
  "expires_in": 7200
}
```

### 错误码

| 错误码 | 错误描述 | 解决方案 |
| --- | --- | --- |
| -1 | system error | 系统繁忙，稍候再试 |
| 40001 | invalid credential | AppSecret 错误或 access_token 无效 |
| 40002 | invalid grant_type | 不合法的凭证类型 |
| 40013 | invalid appid | 不合法的 AppID |
| 40125 | 不合法的 secret | 检查 secret 正确性 |
| 40164 | IP 不在白名单 | 在接口 IP 白名单中设置 |
| 40243 | AppSecret 已被冻结 | 解冻后再调用 |
| 41004 | appsecret missing | 缺少 secret 参数 |
| 50007 | 账号已冻结 | — |

### 适用范围

| 小程序 | 公众号 | 服务号 | 小游戏 | 移动应用 | 网站应用 |
| --- | --- | --- | --- | --- | --- |
| ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |

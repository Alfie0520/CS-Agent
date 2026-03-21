# 发布能力（获取已发布图文消息）

> 来源：https://developers.weixin.qq.com/doc/service/api/public/api_freepublish_batchget.html
> https://developers.weixin.qq.com/doc/service/api/public/api_freepublishgetarticle.html

接口英文名：`freepublish_batchget` / `freepublishGetarticle`

本接口用于获取已成功发布的图文消息列表和详情，主要应用在需要获取公众号历史发布内容的场景。

---

## 接口说明

本接口包含两个主要功能：
1. **批量获取发布文章** (`freepublish_batchget`) - 获取已发布的消息列表
2. **获取单篇文章详情** (`freepublishGetarticle`) - 获取指定文章的详细内容

---

## 1. 批量获取已发布的消息列表

### 调用方式

```bash
POST https://api.weixin.qq.com/cgi-bin/freepublish/batchget?access_token=ACCESS_TOKEN
```

### 请求参数

#### 查询参数 Query String Parameters

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| access_token | string | 是 | 接口调用凭证，可使用 access_token、authorizer_access_token |

#### 请求体 Request Payload

| 参数名 | 类型 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| offset | number | 是 | 0 | 从全部素材的该偏移位置开始返回，0表示从第一个素材返回 |
| count | number | 是 | 10 | 返回素材的数量，取值在1到20之间 |
| no_content | number | 否 | 0 | 1 表示不返回content字段，0表示正常返回，默认为0 |

### 返回参数

#### 返回体 Response Payload

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| total_count | number | 成功发布素材的总数 |
| item_count | number | 本次调用获取的素材的数量 |
| item | objarray | 图文消息条目列表 |

#### Res.item(Array) Object Payload 图文消息条目列表

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| article_id | string | 成功发布的图文消息id |
| content | object | 图文消息内容 |
| update_time | number | 图文消息更新时间 |

#### Res.item(Array).content Object Payload 图文消息内容

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| news_item | objarray | 图文内容列表 |

#### Res.item(Array).content.news_itemObject Payload 图文内容列表

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| title | string | 标题 |
| author | string | 作者 |
| digest | string | 图文消息的摘要，仅有单图文消息才有摘要，多图文此处为空。如果本字段为没有填写，则默认抓取正文前54个字。 |
| content | string | 图文消息的具体内容，支持HTML标签，必须少于2万字符，小于1M，且此处会去除JS,涉及图片url必须来源 "上传图文消息内的图片获取URL"接口获取。外部图片url将被过滤。 |
| content_source_url | string | 图文消息的原文地址，即点击"阅读原文"后的URL |
| thumb_media_id | string | 图文消息的封面图片素材id（必须是永久MediaID） |
| thumb_url | string | 图文消息的封面图片URL |
| need_open_comment | number | 是否打开评论，0不打开(默认)，1打开 |
| only_fans_can_comment | number | 是否粉丝才可评论，0所有人可评论(默认)，1粉丝才可评论 |
| url | string | 草稿的临时链接 |
| is_deleted | boolean | 该图文是否被删除 |

---

## 2. 获取已发布图文信息

### 调用方式

```bash
POST https://api.weixin.qq.com/cgi-bin/freepublish/getarticle?access_token=ACCESS_TOKEN
```

### 请求参数

#### 查询参数 Query String Parameters

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| access_token | string | 是 | 接口调用凭证，可使用 access_token、authorizer_access_token |

#### 请求体 Request Payload

| 参数名 | 类型 | 必填 | 示例 | 说明 |
| --- | --- | --- | --- | --- |
| article_id | string | 是 | ARTICLE_ID | 要获取的草稿的article_id |

### 返回参数

#### 返回体 Response Payload

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| news_item | objarray | 图文信息集合 |
| errcode | number | 错误码 |
| errmsg | string | 错误描述 |

#### Res.news_item(Array) Object Payload 图文信息集合

| 参数名 | 类型 | 说明 |
| --- | --- | --- |
| title | string | 标题 |
| author | string | 作者 |
| digest | string | 图文消息的摘要，仅有单图文消息才有摘要，多图文此处为空。如果本字段为没有填写，则默认抓取正文前54个字。 |
| content | string | 图文消息的具体内容，支持HTML标签，必须少于2万字符，小于1M，且此处会去除JS,涉及图片url必须来源 "上传图文消息内的图片获取URL"接口获取。外部图片url将被过滤。 |
| content_source_url | string | 图文消息的原文地址，即点击"阅读原文"后的URL |
| thumb_media_id | string | 图文消息的封面图片素材id（必须是永久MediaID） |
| thumb_url | string | 图文消息的封面图片URL |
| need_open_comment | number | 是否打开评论，0不打开(默认)，1打开 |
| only_fans_can_comment | number | 是否粉丝才可评论，0所有人可评论(默认)，1粉丝才可评论 |
| url | string | 草稿的临时链接 |
| is_deleted | boolean | 该图文是否被删除 |

---

## 代码示例

### 批量获取发布文章请求示例

```json
{
    "offset": 0,
    "count": 10,
    "no_content": 0
}
```

### 批量获取发布文章返回示例

```json
{
    "total_count": 100,
    "item_count": 10,
    "item": [
        {
            "article_id": "ARTICLE_ID_1",
            "update_time": 1234567890,
            "content": {
                "news_item": [
                    {
                        "title": "文章标题",
                        "author": "作者名称",
                        "digest": "文章摘要",
                        "content": "文章内容HTML",
                        "content_source_url": "https://example.com",
                        "thumb_media_id": "THUMB_MEDIA_ID",
                        "thumb_url": "https://example.com/thumb.jpg",
                        "need_open_comment": 1,
                        "only_fans_can_comment": 0,
                        "url": "https://mp.weixin.qq.com/s/xxx",
                        "is_deleted": false
                    }
                ]
            }
        }
    ]
}
```

### 获取单篇文章详情请求示例

```json
{
    "article_id": "ARTICLE_ID_1"
}
```

### 获取单篇文章详情返回示例

```json
{
    "news_item": [
        {
            "title": "文章标题",
            "author": "作者名称",
            "digest": "文章摘要",
            "content": "文章内容HTML",
            "content_source_url": "https://example.com",
            "thumb_media_id": "THUMB_MEDIA_ID",
            "thumb_url": "https://example.com/thumb.jpg",
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
            "url": "https://mp.weixin.qq.com/s/xxx",
            "is_deleted": false
        }
    ],
    "errcode": 0,
    "errmsg": "ok"
}
```

---

## 错误码

以下是本接口的错误码列表，其他错误码可参考通用错误码；调用接口遇到报错，可使用官方提供的API诊断工具辅助定位和分析问题。

| 错误码 | 错误描述 | 解决方案 |
| --- | --- | --- |
| 0 | ok | 成功 |
| 48001 | api unauthorized | api功能未授权，请确认公众号/服务号已获得该接口，可以在「公众平台官网-开发者中心页」中查看接口权限 |
| 53600 | Article ID 无效 | 无效的文章ID |

---

## 适用范围

本接口在不同账号类型下的可调用情况：

| 公众号 | 服务号 |
| --- | --- |
| 仅认证 ✔ | 仅认证 ✔ |

仅认证：表示仅允许企业主体已认证账号调用，未认证或不支持认证的账号无法调用。✔：该账号可调用此接口。其他未明确声明的账号类型，如无特殊说明，均不可调用此接口。

---

## 注意事项

1. 本接口应在服务器端调用，不可在前端（小程序、网页、APP等）直接调用
2. 本接口不支持云调用
3. 本接口支持第三方平台代商家调用
4. 该接口所属的权限集id为：7
5. 服务商获得权限集授权后，可通过使用authorizer_access_token代商家进行调用
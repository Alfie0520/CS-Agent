# CS-Agent

微信服务号自动化客服 Agent 后台服务。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 AppID / AppSecret / Token

# 3. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 80
```

## 项目结构

```
app/
├── main.py              # FastAPI 入口 + Webhook 端点
├── config.py            # 配置管理
├── core/
│   ├── security.py      # 签名校验
│   └── xml_parser.py    # XML 解析/构建
├── models/
│   └── message.py       # 消息数据模型
├── wechat_api/
│   ├── client.py        # 微信 API 客户端
│   ├── token_manager.py # Access Token 管理
│   └── customer_message.py  # 客服消息发送
├── handler/
│   ├── router.py        # 消息分发路由
│   ├── message_handler.py   # 普通消息处理
│   └── event_handler.py     # 事件处理
└── agent/
    ├── base.py          # Agent 抽象接口
    └── default_agent.py # 默认回复 Agent
```

## 消息流转

```
用户发消息 → 微信服务器 POST /wx → 立即返回 "success"
                                  → BackgroundTask 异步处理
                                  → Agent 生成回复
                                  → 客服消息接口发送给用户
```

特殊情况：用户发送「转人工」→ 同步返回 `transfer_customer_service` XML，微信将后续会话转交人工客服。

## 微信开发者平台配置

1. 服务器 URL：`http://your-server-ip/wx`
2. Token：与 `.env` 中 `WECHAT_TOKEN` 保持一致
3. 消息加密方式：明文模式（开发阶段）

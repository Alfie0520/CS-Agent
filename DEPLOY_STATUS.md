# 部署进度跟踪

> 服务器：Ubuntu (VM-0-12-ubuntu) — 腾讯云轻量应用服务器（香港）  
> 公网 IP：43.129.183.181  
> 代码路径：/opt/CS-Agent  
> 服务名：cs-agent.service

---

## 阶段一：测试号验证 ✅ 已完成

测试号 appID：`wx944e56b778966bf6`  
测试号链接：https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login

### 已完成

- [x] 服务器环境准备：Python 3.10 + pip + nginx
- [x] 部署代码：git clone → /opt/CS-Agent，venv + 依赖安装
- [x] nginx 反向代理：80 → 127.0.0.1:8000（配置 /etc/nginx/sites-available/cs-agent）
- [x] systemd 服务：cs-agent.service 开机自启 + 崩溃重启
- [x] 防火墙：TCP 80 已放行
- [x] .env 配置：测试号 appID / appsecret / token
- [x] 测试号接口配置验证通过：URL = `http://43.129.183.181/wx`
- [x] 端到端消息收发验证通过

### 踩过的坑

1. **pydantic ValidationError**：.env 未配置导致启动失败 → 需先 `cp .env.example .env` 再填值
2. **Token 不一致**：.env 中 Token 与测试号页面填写的不同 → 两边必须完全一致
3. **防火墙**：轻量应用服务器用「防火墙」而非「安全组」→ 需在实例详情页的防火墙标签添加规则
4. **WebFetch 超时**：外部工具无法访问但微信服务器可以 → 以 nginx access.log 为准判断连通性

---

## 阶段二：代码加固（接入正式服务号前必做）

### 关键修复（Critical）

- [ ] **POST 签名验证**：当前 POST /wx 未校验签名，存在伪造消息风险
- [ ] **XML 注入防护**：CDATA 中 `]]>` 可导致注入，需转义
- [ ] **HTTP 响应校验**：wechat_api/client.py 未检查状态码和 JSON 解析失败
- [ ] **Token 刷新容错**：刷新失败时无重试，get_token() 可能返回空值
- [ ] **Token 刷新竞态**：并发调用 get_token() 可能触发多次刷新，需加锁

### 重要改进（Warning）

- [ ] XML 解析异常捕获：malformed XML / 未知 MsgType 应 graceful 降级
- [ ] HTTP client 生命周期：httpx.AsyncClient 全局实例未在 shutdown 时关闭
- [ ] 消息去重线程安全：_seen_msg_ids 需用 asyncio.Lock 保护
- [ ] 客服消息发送响应校验：检查 errcode 并记录错误
- [ ] BackgroundTask 异常兜底：后台任务异常需 log，避免静默失败

### 建议优化（Suggestion）

- [ ] 添加 `/health` 健康检查端点
- [ ] 添加请求速率限制
- [ ] 实现消息加密/解密（正式号可能要求安全模式）
- [ ] 日志脱敏：避免记录用户原始消息内容
- [ ] Agent 实例依赖注入，便于测试和替换

---

## 阶段三：正式服务号上线

### 前置条件

- [ ] 域名申请 + ICP 备案（备案约 1-2 周）
- [ ] 阶段二关键修复全部完成

### 上线步骤

1. **DNS 配置**：域名 A 记录 → 43.129.183.181
2. **nginx 更新**：server_name 改为域名，可选配置 HTTPS（Let's Encrypt）
3. **管理员扫码开启 AppSecret**
4. **.env 更新**：替换为正式服务号的 appID / appSecret / token
5. **微信开发者平台配置**：
   - 服务器 URL：`https://yourdomain.com/wx`
   - Token：与 .env 一致
   - 消息加密方式：建议安全模式（需实现加解密）
6. **IP 白名单**：将 43.129.183.181 加入开发者平台 API 白名单
7. **重启服务** + 端到端测试
8. **监控部署**：日志告警 + 服务可用性监控

---

## 常用运维命令

```bash
# 服务管理
sudo systemctl restart cs-agent
sudo systemctl status cs-agent

# 日志查看
sudo journalctl -u cs-agent -f          # 实时日志
sudo journalctl -u cs-agent -n 50       # 最近 50 行
sudo tail -f /var/log/nginx/access.log  # nginx 访问日志

# nginx
sudo nginx -t && sudo systemctl reload nginx

# 代码更新
cd /opt/CS-Agent && git pull && sudo systemctl restart cs-agent
```

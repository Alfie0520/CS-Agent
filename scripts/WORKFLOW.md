# 参访方案数据更新工作流

## 项目背景

这是一个**游学方案管理系统**，用于管理企业参访学习的资源和信息。

**核心功能**：
- 管理标杆企业数据库（企业信息、主题、城市等）
- 管理参访方案中的图片素材（微信永久素材库）

**关键数据文件**：
| 文件 | 用途 | 位置 |
|------|------|------|
| `enterprises.json` | 标杆企业数据库，供给前端展示 | `app/data/enterprises.json` |
| `media_index.json` | 参访方案图片索引，记录微信素材的 media_id | 服务器 `/data/media_index.json` |
| `2026游学资源表.xlsx` | 企业数据源，由业务方提供 | `scripts/enterprise_db/data/` |

**相关API**：
- `POST https://43.129.183.181/api/visit-image` - 处理图片的增删改操作

---

## 远程服务器信息

- **IP**: `43.129.183.181`
- **SSH 用户**: `ubuntu`
- **SSH 密码**: `Alfie000301`
- **媒体索引文件**: `/data/media_index.json`（服务器上的文件）
- **API 地址**: `https://43.129.183.181/api/visit-image`

---

## 项目文件结构

```
CS-Agent/
├── app/
│   └── data/
│       └── enterprises.json          # 标杆企业数据库（前端使用）
├── scripts/
│   ├── image_ops/                   # 图片素材管理
│   │   ├── batch_image_operations.py # 批量图片操作脚本（调用远程API）
│   │   └── data/
│   │       ├── images/             # 图片文件目录
│   │       └── ops.json            # 图片操作配置
│   └── enterprise_db/              # 企业数据管理
│       ├── build_enterprise_db.py   # 从Excel生成JSON的脚本
│       └── data/
│           └── 2026游学资源表.xlsx  # 源数据表格（文件名必须严格匹配）
```

---

## 工作流一：图片素材更新

### 背景
当参访方案需要更新图片时（如新增企业考察点、更换图片），通过此流程更新微信素材库和索引。

**涉及的微信概念**：
- `media_id`：微信永久素材的唯一标识
- `category`：图片分类，命名规则如 `05浙江`、`广东-深圳`、`09河南` 等

### 步骤

#### 步骤1：用户放置图片
用户将需要处理的图片放入 `scripts/image_ops/data/images/` 目录。

**目录结构示例**：
```
scripts/image_ops/data/images/
├── 杭州/
│   ├── 兔宝宝.png
│   └── 恒生电子.png
├── 广东-深圳/
│   └── 华为松山湖.png
└── 09河南/
    └── 胖东来.png
```

**说明**：
- 图片可以按城市/省份分组存放（仅用于组织文件，category 由后续配置决定）
- 支持格式：`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`

放置完成后，告知 agent 需要处理哪些图片。

#### 步骤2：Agent 连接服务器检查现有数据
SSH 登录服务器，查看 `media_index.json` 确认：
- 哪些图片已存在（需要更新还是新增？）
- 需要删除的旧图片的 `media_id`
- 目标 `category` 的正确名称

```python
import paramiko
import json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('43.129.183.181', username='ubuntu', password='Alfie000301')

# 获取媒体索引
stdin, stdout, stderr = client.exec_command('cat /data/media_index.json')
media_index = json.loads(stdout.read().decode())
print(f"总记录数: {len(media_index)}")

# 查找特定企业
for item in media_index:
    if '企业名' in item.get('image_name', ''):
        print(item)

# 查看所有 category 及其数量
categories = {}
for item in media_index:
    cat = item.get('category', 'Unknown')
    categories[cat] = categories.get(cat, 0) + 1
for cat, count in sorted(categories.items()):
    print(f"  {cat}: {count}")
```

#### 步骤3：向用户确认操作
向用户确认：
- 每张图片是**新增**还是**更新**
- 对应的企业名称和所在城市（用于确定正确的 `category`）
- 是否需要**删除**某些旧图片（需提供 `media_id`）

**常见问题**：
- 如果图片中的企业在 `enterprises.json` 中已存在，category 通常与该企业的城市对应
- 如果不确定 category，可以先在服务器上搜索同名企业的记录

#### 步骤4：配置 ops.json
在 `scripts/image_ops/data/ops.json` 中配置操作：

```json
{
  "operations": [
    {
      "operation": "create",
      "image_path": "images/杭州/兔宝宝.png",
      "image_name": "兔宝宝.png",
      "category": "05浙江"
    },
    {
      "operation": "update",
      "image_path": "images/广东-深圳/华为更新.png",
      "image_name": "华为.png",
      "category": "广东-深圳",
      "media_id": "原有的media_id"
    },
    {
      "operation": "delete",
      "media_id": "要删除的media_id"
    }
  ]
}
```

**operation 字段说明**：
| operation | 必填字段 | 说明 |
|-----------|---------|------|
| `create` | `image_path`, `image_name`, `category` | 上传新图片到微信素材库 |
| `update` | `image_path`, `image_name`, `category`, `media_id` | 更新已存在的图片 |
| `delete` | `media_id` | 从微信素材库删除图片 |

**字段说明**：
- `image_path`：相对于 `scripts/image_ops/data/` 目录的路径
- `image_name`：图片在微信素材库中的名称
- `category`：分类，用于组织和标识
- `media_id`：微信素材的唯一标识，从服务器获取

#### 步骤5：运行脚本
```bash
cd /path/to/CS-Agent
python3 scripts/image_ops/batch_image_operations.py
```

**脚本行为**：
1. 读取 `ops.json` 配置
2. 对每张图片进行压缩（目标 200KB 以内）
3. 调用远程 API 执行操作
4. 输出执行结果

#### 步骤6：验证服务器结果
再次连接服务器，检查 `media_index.json` 是否正确更新：

```python
stdin, stdout, stderr = client.exec_command('cat /data/media_index.json')
media_index = json.loads(stdout.read().decode())
print(f"总记录数: {len(media_index)}")

# 验证新增的图片是否存在
for item in media_index:
    if '兔宝宝' in item.get('image_name', ''):
        print(f"新增成功: {item}")
```

---

## 工作流二：企业数据更新

### 背景
当业务方提供新的 `2026游学资源表.xlsx` 时，需要将其转换为 `enterprises.json` 供前端使用。

### 前置条件
工作流一（图片更新）已成功完成。

### 步骤

#### 步骤1：向用户确认
询问用户 `scripts/enterprise_db/data/` 目录下的表格是否是最新的。

如果用户确认有新表格，继续步骤2。

#### 步骤2：检查并重命名文件（如需要）
如果文件名不是 `2026游学资源表.xlsx`，需要重命名：
```bash
mv "2026游学资源表(1).xlsx" "2026游学资源表.xlsx"
```

#### 步骤3：运行脚本
```bash
cd /path/to/CS-Agent
python3 scripts/enterprise_db/build_enterprise_db.py
```

**脚本行为**：
1. 读取 Excel 文件的 "标杆企业" 工作表
2. 解析企业数据（编号、城市、名称、主题等）
3. 生成 JSON 文件到 `app/data/enterprises.json`
4. 输出记录数量

#### 步骤4：验证结果
脚本会输出类似：
```
完成：共写入 404 条企业数据 → /Users/alfie/vibe_coding/CS-Agent/app/data/enterprises.json
```

可以对比新旧版本的差异：

```python
import json

with open('app/data/enterprises.json') as f:
    new = json.load(f)

# 检查新增的企业
print(f"总记录数: {len(new)}")
print(f"最新ID: {max(e['id'] for e in new)}")
```

---

## 两个工作流的关系

工作流一和工作流二是**串行执行**的：

```
用户放置图片
    ↓
工作流一：图片更新
    ↓（成功后）
向用户确认表格是否更新
    ↓
工作流二：企业数据更新
    ↓
完成
```

通常业务方更新企业数据时，也会同步更新参访方案图片，所以两者需要按顺序执行。

---

## 技术细节

### 图片压缩
- 目标大小：200KB 以内
- 压缩策略：
  1. 逐步缩小尺寸（100% → 50% → 25% → 10%）
  2. 逐步降低质量（85 → 70 → 55 → 40 → 30）
  3. 最终质量 20%

### API Key
`batch_image_operations.py` 中硬编码了 API Key：
```python
REMOTE_API_KEY = "cRgCWNHkfrZt7GE47JQtyE9RDY2Pxo4lAs9DQjuSXUY="
```
用于认证请求到远程 API。

### SSL 证书
服务器使用 HTTPS 但证书是颁发给域名的，直接用 IP 访问会证书验证失败。脚本中已设置 `verify=False` 跳过验证。

### 服务器权限
`/data/media_index.json` 文件所有者是 `root`，权限 `644`。如果遇到写入问题，在服务器上执行：
```bash
sudo chmod 666 /data/media_index.json
```

---

## 快速命令参考

```bash
# 图片更新
python3 scripts/image_ops/batch_image_operations.py

# 企业数据更新
python3 scripts/enterprise_db/build_enterprise_db.py

# SSH 连接服务器
ssh ubuntu@43.129.183.181
# 密码: Alfie000301
```
# 开发者 API 文档

## 概述

开发者 Token 系统允许管理员创建和管理 API 访问令牌，用于第三方应用或脚本访问 JiETNG 的 API 端点。

## 快速开始

### 获取 API Token

如果您想使用 JiETNG API，请按照以下步骤获取访问令牌：

1. **发送邮件**
   - 收件人: `matsuk1@proton.me`
   - 主题: `JiETNG API Token Request`
   - 内容:
     - 您的姓名或组织名称
     - 使用目的说明
     - 预计使用频率

2. **等待审核**
   - 管理员会审核您的申请并创建专属 Token

3. **接收 Token**
   - 您将通过邮件收到 Token ID 和完整的 Token 字符串
   - **请妥善保管好您的 Token！**

### API 基础信息

- **Base URL**: `https://jietng.matsuki.top/api/v1/`
- **认证方式**: Bearer Token
- **响应格式**: JSON

### 使用示例

```bash
# 使用您的 Token 访问 API
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     "https://jietng.matsuki.top/api/v1/users"
```

## 命令使用

### 管理员命令

仅管理员可在 LINE Bot 中使用以下命令：

#### 1. 创建 Token

```
devtoken create <备注说明>
```

**示例:**
```
devtoken create MyApp API Integration
```

**返回:**
- Token ID（用于管理）
- 完整的 Token 字符串（请妥善保管）
- 备注说明

#### 2. 列出所有 Token

```
devtoken list
```

**显示内容:**
- Token ID
- 备注
- 状态（Active/Revoked）
- 创建时间
- 最后使用时间

#### 3. 撤销 Token

```
devtoken revoke <token_id>
```

**示例:**
```
devtoken revoke jt_abc123def456
```

#### 4. 查看 Token 详情

```
devtoken info <token_id>
```

**显示内容:**
- Token ID
- 完整 Token 字符串
- 备注
- 状态
- 创建者
- 创建时间
- 最后使用时间

## API 使用

### Base URL

```
https://jietng.matsuki.top/api/v1/
```

### 认证

所有 API 端点都需要 Bearer Token 认证：

```bash
curl -H "Authorization: Bearer <your_token>" https://jietng.matsuki.top/api/v1/...
```

### 可用端点

以下所有端点的完整 URL 为 `https://jietng.matsuki.top/api/v1/` + 端点路径。

#### 1. 获取用户列表

```http
GET /api/v1/users
```

**示例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/users
```

**响应:**
```json
{
  "success": true,
  "count": 100,
  "users": [
    {
      "user_id": "U123456",
      "nickname": "ユーザー名"
    },
    ...
  ]
}
```

#### 2. 注册用户

```http
POST /api/v1/register/<user_id>
```

**请求体 (JSON):**
- `nickname`: **必需**，用户昵称（如果是LINE用户会自动从LINE API获取，非LINE用户则使用此参数）
- `language`: 语言设置 (ja/en/zh，可选，默认 en)

**昵称获取优先级:**
1. 从 LINE API 自动获取（如果是 LINE 用户）
2. 从用户数据中的 nickname 字段获取
3. 使用参数提供的 nickname

**示例:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." -H "Content-Type: application/json" -d '{"nickname":"TestUser","language":"en"}' https://jietng.matsuki.top/api/v1/register/U123456
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "nickname": "TestUser",
  "bind_url": "https://jietng.matsuki.top/linebot/sega_bind?token=xxx&nickname=TestUser&language=en",
  "token": "xxx",
  "expires_in": 120,
  "message": "Bind URL generated successfully. Token expires in 2 minutes."
}
```

**注册记录:**

通过 API 注册的新用户会自动记录以下信息：
- `registered_via_token`: 注册时使用的 token ID
- `registered_at`: 注册时间（格式：YYYY-MM-DD HH:MM:SS）

#### 3. 获取用户信息

```http
GET /api/v1/user/<user_id>
```

**示例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/user/U123456
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "nickname": "ユーザー名",
  "data": {
    "language": "ja",
    "sega_id": "...",
    ...
  }
}
```

#### 4. 删除用户

```http
DELETE /api/v1/user/<user_id>
```

**示例:**
```bash
curl -X DELETE -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/user/U123456
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "message": "User U123456 has been deleted successfully"
}
```

#### 5. 队列用户更新

```http
POST /api/v1/update/<user_id>
```

**示例:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/update/U123456
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "task_id": "task_xxx",
  "queue_size": 5,
  "message": "User update task queued successfully"
}
```

#### 6. 查询任务状态

```http
GET /api/v1/task/<task_id>
```

**说明:**
查询通过 `/update/<user_id>` 创建的更新任务的执行状态。

**示例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/task/task_xxx
```

**响应:**

**任务进行中:**
```json
{
  "success": true,
  "task_id": "task_xxx",
  "status": "pending",
  "message": "Task is still in queue or processing"
}
```

**任务已完成:**
```json
{
  "success": true,
  "task_id": "task_xxx",
  "status": "completed",
  "result": {
    // 更新任务的结果数据
  }
}
```

**任务不存在或已过期:**
```json
{
  "success": false,
  "task_id": "task_xxx",
  "status": "not_found",
  "message": "Task not found or has expired"
}
```

#### 7. 获取用户记录

```http
GET /api/v1/records/<user_id>?type=<record_type>&command=<filter>
```

**参数:**
- `type`: 记录类型 (best50/best100/best35/best15/allb50/allb35/apb50/rct50/idealb50，可选，默认 best50)
- `command`: 筛选命令（可选，支持 -ver、-fc、-rate 等）

**示例:**
```bash
# 获取 best50
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/records/U123456?type=best50"

# 筛选特定版本
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/records/U123456?type=best50&command=-ver%20DX%20FESTiVAL%20PLUS"
```

**响应:**
```json
{
  "success": true,
  "old_songs": [...],
  "new_songs": [...]
}
```

#### 8. 搜索歌曲

```http
GET /api/v1/search?q=<query>&user_id=<user_id>&ver=<version>&max_results=<limit>
```

**参数:**
- `q`: 搜索关键词（可选，默认空字符串；使用 `__empty__` 表示显式空字符串）
- `user_id`: 在指定用户的成绩数据库内匹配歌曲（默认为空，不匹配）
- `ver`: 版本 (jp/intl，可选，默认 jp，填写 user_id 后可省略)
- `max_results`: 最大返回结果数（可选，默认 6）

**示例:**
```bash
# 搜索日文歌曲
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=%E3%83%92%E3%83%90%E3%83%8A&ver=jp"

# 搜索空字符串歌名
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=__empty__&ver=jp"

# 在用户的成绩数据库内匹配
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=%E3%83%92%E3%83%90%E3%83%8A&user_id=U123456"
```

**响应:**
```json
{
  "success": true,
  "count": 2,
  "songs": [
    {
      "title": "ヒバナ",
      "artist": "Artist Name",
      ...
    },
    ...
  ]
}
```

```json
{
  "success": true,
  "count": 2,
  "records": [
    [
      {
        "name": "ヒバナ",
        "score": "100.8828%",
        ...
      },
      ...
    ],
    ...
  ]
}
```

#### 9. 获取版本列表

```http
GET /api/v1/versions
```

**示例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/versions
```

**响应:**
```json
{
  "success": true,
  "versions": [
    {"id": 0, "name": "maimai"},
    {"id": 1, "name": "maimai PLUS"},
    ...
  ]
}
```

## 权限请求 API

权限请求系统允许开发者 Token 请求访问不是由该 Token 创建的用户数据。用户可以批准或拒绝这些请求。

### 权限模型

JiETNG 使用两层权限模型：

1. **所有者权限（Owner）**：创建用户的 Token（通过 `registered_via_token` 字段标识）
   - 可以执行所有操作：读取、更新、删除用户
   - 可以管理权限请求：查看、批准、拒绝、撤销

2. **授权访问权限（Granted）**：被用户授权的 Token（在 Token 的 `allowed_users` 列表中）
   - 可以读取用户数据
   - 可以触发用户数据更新
   - **不能**删除用户或管理权限

### 装饰器说明

API 使用两种装饰器来控制访问权限：

- **`@require_user_permission`**：允许所有者和被授权者访问（用于读取操作）
- **`@require_owner_permission`**：只允许所有者访问（用于敏感操作）

#### 10. 请求访问权限

```http
POST /api/v1/perm/<user_id>
```

**说明：** 向指定用户发送权限请求，请求访问该用户的数据。

**权限要求：** 任何有效的开发者 Token

**请求体 (JSON):**
- `requester_name`: 可选，请求者名称（用于在通知中显示，默认使用 Token 的备注）

**示例:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"requester_name":"MyApp"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456
```

**响应:**
```json
{
  "success": true,
  "request_id": "20250203120000_jt_abc123",
  "user_id": "U123456",
  "message": "Permission request sent to user U123456"
}
```

**错误响应：**
```json
{
  "error": "Permission already granted",
  "message": "Token already has access to user U123456"
}
```

```json
{
  "error": "Request already sent",
  "message": "Permission request already sent, waiting for approval"
}
```

#### 11. 查看权限请求列表

```http
GET /api/v1/perm/<user_id>/requests
```

**说明：** 获取用户的待处理权限请求列表。

**权限要求：** 只有所有者 Token（`@require_owner_permission`）

**示例:**
```bash
curl -H "Authorization: Bearer abc123..." \
     https://jietng.matsuki.top/api/v1/perm/U123456/requests
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "count": 2,
  "requests": [
    {
      "request_id": "20250203120000_jt_abc123",
      "token_id": "jt_abc123",
      "token_note": "MyApp",
      "requester_name": "MyApp",
      "timestamp": "2025-02-03 12:00:00"
    },
    {
      "request_id": "20250203130000_jt_def456",
      "token_id": "jt_def456",
      "token_note": "AnotherApp",
      "requester_name": "AnotherApp",
      "timestamp": "2025-02-03 13:00:00"
    }
  ]
}
```

#### 12. 批准权限请求

```http
POST /api/v1/perm/<user_id>/accept
```

**说明：** 批准指定的权限请求，将请求的 Token 添加到授权列表。

**权限要求：** 只有所有者 Token（`@require_owner_permission`）

**请求体 (JSON):**
- `request_id`: **必需**，要批准的权限请求ID

**示例:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"request_id":"20250203120000_jt_abc123"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/accept
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "token_id": "jt_abc123",
  "token_note": "MyApp",
  "message": "Permission granted to token jt_abc123"
}
```

**错误响应：**
```json
{
  "error": "Request not found",
  "message": "Permission request not found or already processed"
}
```

#### 13. 拒绝权限请求

```http
POST /api/v1/perm/<user_id>/reject
```

**说明：** 拒绝指定的权限请求。

**权限要求：** 只有所有者 Token（`@require_owner_permission`）

**请求体 (JSON):**
- `request_id`: **必需**，要拒绝的权限请求ID

**示例:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"request_id":"20250203120000_jt_abc123"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/reject
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "token_id": "jt_abc123",
  "token_note": "MyApp",
  "message": "Permission request from token jt_abc123 rejected"
}
```

#### 14. 撤销已授予的权限

```http
POST /api/v1/perm/<user_id>/revoke
```

**说明：** 撤销已授予给指定 Token 的访问权限。

**权限要求：** 只有所有者 Token（`@require_owner_permission`）

**请求体 (JSON):**
- `token_id`: **必需**，要撤销权限的 Token ID

**示例:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"token_id":"jt_abc123"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/revoke
```

**响应:**
```json
{
  "success": true,
  "user_id": "U123456",
  "token_id": "jt_abc123",
  "message": "Permission revoked for token jt_abc123"
}
```

**错误响应：**
```json
{
  "error": "Permission not found",
  "message": "Token jt_abc123 does not have permission to access user U123456"
}
```

### 权限请求工作流程示例

```bash
# 1. Token B 请求访问由 Token A 创建的 User1
curl -X POST -H "Authorization: Bearer TOKEN_B" \
     -H "Content-Type: application/json" \
     -d '{"requester_name":"MyApp"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456

# 2. Token A（所有者）查看待处理的权限请求
curl -H "Authorization: Bearer TOKEN_A" \
     https://jietng.matsuki.top/api/v1/perm/U123456/requests

# 3. Token A 批准请求
curl -X POST -H "Authorization: Bearer TOKEN_A" \
     -H "Content-Type: application/json" \
     -d '{"request_id":"20250203120000_jt_tokenb"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/accept

# 4. 现在 Token B 可以访问 User1 的数据
curl -H "Authorization: Bearer TOKEN_B" \
     https://jietng.matsuki.top/api/v1/user/U123456

# 5. （可选）Token A 撤销 Token B 的访问权限
curl -X POST -H "Authorization: Bearer TOKEN_A" \
     -H "Content-Type: application/json" \
     -d '{"token_id":"jt_tokenb"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/revoke
```

### LINE 用户的权限管理

LINE 用户会收到权限请求的 FlexMessage 通知，可以直接在 LINE 中批准或拒绝：

1. 当有新的权限请求时，用户会收到通知消息
2. 消息包含请求者信息和两个按钮："承認"（批准）和"拒否"（拒绝）
3. 点击按钮后，系统会自动处理请求

## 错误处理

### 401 Unauthorized

**情况:**
- 未提供 Authorization header
- Token 格式错误
- Token 无效或已被撤销

**响应示例:**
```json
{
  "error": "Invalid token",
  "message": "Token is invalid or has been revoked"
}
```

### 400 Bad Request

**情况:**
- 缺少必需参数（例如：register 端点缺少 nickname）
- 参数值无效（例如：language 不在允许列表中）

**响应示例:**
```json
{
  "error": "Missing parameter",
  "message": "Parameter 'nickname' is required"
}
```

### 403 Forbidden

**情况:**
- 当前 token 无法访问该 user_id
- Token 不是用户的所有者（对于需要所有者权限的操作）
- Token 既不是所有者也未被授权访问

**响应示例:**
```json
{
  "error": "Forbidden",
  "message": "Only the owner token (creator) can perform this operation"
}
```

```json
{
  "error": "Permission denied",
  "message": "Token does not have permission to access user U123456"
}
```

### 404 Not Found

**情况:**
- 请求的资源不存在（例如：用户不存在）

**响应示例:**
```json
{
  "error": "User not found",
  "message": "User U123456 does not exist"
}
```

### 500 Internal Server Error

**情况:**
- 服务器内部错误

**响应示例:**
```json
{
  "error": "Internal server error",
  "message": "Error description"
}
```

## API 端点汇总

### 基础端点

| 端点 | 方法 | 说明 | 权限要求 |
|----------------|--------------|-------------------|----------|
| `/users` | GET | 获取所有用户列表 | 任何 Token |
| `/register/<user_id>` | POST | 注册用户并生成绑定链接 | 任何 Token |
| `/user/<user_id>` | GET | 获取用户信息 | 所有者或被授权 |
| `/user/<user_id>` | DELETE | 删除用户 | **仅所有者** |
| `/update/<user_id>` | POST | 队列用户数据更新 | 所有者或被授权 |
| `/task/<task_id>` | GET | 查询任务状态 | 任何 Token |
| `/records/<user_id>` | GET | 获取用户成绩记录 | 所有者或被授权 |
| `/search` | GET | 搜索歌曲 | 任何 Token |
| `/versions` | GET | 获取版本列表 | 任何 Token |

### 权限管理端点

| 端点 | 方法 | 说明 | 权限要求 |
|----------------|--------------|-------------------|----------|
| `/perm/<user_id>` | POST | 请求访问权限 | 任何 Token |
| `/perm/<user_id>/requests` | GET | 查看权限请求列表 | **仅所有者** |
| `/perm/<user_id>/accept` | POST | 批准权限请求 | **仅所有者** |
| `/perm/<user_id>/reject` | POST | 拒绝权限请求 | **仅所有者** |
| `/perm/<user_id>/revoke` | POST | 撤销已授予的权限 | **仅所有者** |

## 安全建议

1. **妥善保管 Token**
   - Token 只在创建时显示一次
   - 请将 Token 保存在安全的位置
   - 不要在公共代码库中提交 Token

2. **定期轮换 Token**
   - 定期撤销旧 Token 并创建新 Token
   - 为不同的应用使用不同的 Token

3. **使用 HTTPS**
   - 始终通过 HTTPS 传输 Token
   - 避免在不安全的网络中使用 API

4. **监控使用情况**
   - 定期检查 Token 的最后使用时间
   - 撤销不再使用的 Token

5. **最小权限原则**
   - 只为需要的应用创建 Token
   - 及时撤销不再需要的访问权限

## 技术实现

### 数据存储

Token 数据存储位置由 `config.json` 中的 `file_path.dev_tokens` 配置项决定（默认：`./data/dev_tokens.json`）：

```json
{
  "jt_abc123def456": {
    "token": "actual_token_string",
    "note": "MyApp API Integration",
    "created_at": "2025-01-24 12:00:00",
    "created_by": "U123456",
    "last_used": "2025-01-24 15:30:00",
    "revoked": false
  }
}
```

### 装饰器使用

在新的 API 端点中使用 `@require_dev_token` 装饰器：

```python
@app.route("/api/v1/my_endpoint", methods=["GET"])
@csrf.exempt
@require_dev_token
def my_api_endpoint():
    # Token 信息会自动添加到 request.token_info
    token_info = request.token_info
    logger.info(f"API access via token {token_info['token_id']}")

    return jsonify({"success": True})
```

## 示例代码

### Python

```python
import requests

TOKEN = "your_token_here"
BASE_URL = "https://jietng.matsuki.top/api/v1"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# 获取用户列表
response = requests.get(f"{BASE_URL}/users", headers=headers)
users = response.json()

print(f"Total users: {users['count']}")
for user in users['users']:
    print(f"  - {user['nickname']} ({user['user_id']})")
```

### JavaScript

```javascript
const TOKEN = 'your_token_here';
const BASE_URL = 'https://jietng.matsuki.top/api/v1';

async function getUsers() {
  const response = await fetch(`${BASE_URL}/users`, {
    headers: {
      'Authorization': `Bearer ${TOKEN}`
    }
  });

  const data = await response.json();
  console.log(`Total users: ${data.count}`);

  data.users.forEach(user => {
    console.log(`  - ${user.nickname} (${user.user_id})`);
  });
}

getUsers();
```

### cURL

```bash
#!/bin/bash

TOKEN="your_token_here"
BASE_URL="https://jietng.matsuki.top/api/v1"

# 获取用户列表
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/users"

# 获取特定用户信息
USER_ID="U123456"
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/user/$USER_ID"

# 搜索歌曲
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/search?q=ヒバナ&ver=jp"
```

## 常见问题

### Q: Token 会过期吗？
**A:** 目前 Token 不会自动过期，但可以被管理员手动撤销。

### Q: 丢失 Token 怎么办？
**A:** Token 只在创建时显示一次。如果丢失，需要撤销旧 Token 并创建新的。

### Q: 一个应用可以有多个 Token 吗？
**A:** 可以。建议为不同的用途创建不同的 Token，便于管理和撤销。

### Q: Token 的权限范围是什么？
**A:** JiETNG 实现了两层权限模型：
- **所有者权限**：创建用户的 Token 拥有完整权限（读取、更新、删除用户，管理权限请求）
- **授权访问权限**：被用户授权的 Token 只能读取和更新用户数据，不能删除用户或管理权限

## 版本历史

- **v1.1** (2025-02-03): 添加权限请求系统
  - 新增 5 个权限管理 API 端点
  - 实现两层权限模型（所有者 vs 被授权者）
  - 添加 `@require_owner_permission` 装饰器
  - LINE 用户支持 FlexMessage 权限请求通知
- **v1.0** (2025-01-24): 初始版本，支持基本的 Token 管理和 API 认证

## 相关文件

- `config.json` - 配置文件（包含 Token 文件路径）
- `modules/config_loader.py` - 配置加载器
- `modules/devtoken_manager.py` - Token 管理核心逻辑
- `modules/perm_request_handler.py` - 权限请求处理逻辑
- `modules/perm_request_generator.py` - 权限请求 FlexMessage 生成器
- `modules/message_manager.py` - 三语消息定义
- `main.py` - API 端点和命令处理
- `data/dev_tokens.json` - Token 数据存储（默认位置）

## 支持

如有问题或建议，请联系系统管理员（邮箱：matsuk1@proton.me）。

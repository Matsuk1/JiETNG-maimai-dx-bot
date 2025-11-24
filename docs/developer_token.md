# 开发者 Token 管理系统 / Developer Token Management System

## 概述 / Overview

开发者 Token 系统允许管理员创建和管理 API 访问令牌，用于第三方应用或脚本访问 JiETNG 的 API 端点。

The Developer Token system allows administrators to create and manage API access tokens for third-party applications or scripts to access JiETNG's API endpoints.

---

## 功能特性 / Features

- ✅ 创建安全的 API Token（使用 `secrets.token_urlsafe(32)`）
- ✅ 为每个 Token 添加备注说明
- ✅ 列出所有 Token 及其状态
- ✅ 撤销不再需要的 Token
- ✅ 查看 Token 详细信息
- ✅ 自动记录 Token 最后使用时间
- ✅ Bearer Token 认证装饰器
- ✅ 三语支持（日语/英语/中文）

---

## 命令使用 / Command Usage

### 管理员命令 / Admin Commands

仅管理员可在 LINE Bot 中使用以下命令：

Only administrators can use the following commands in LINE Bot:

#### 1. 创建 Token / Create Token

```
devtoken create <备注说明>
```

**示例 / Example:**
```
devtoken create MyApp API Integration
```

**返回 / Response:**
- Token ID（用于管理）
- 完整的 Token 字符串（请妥善保管）
- 备注说明

#### 2. 列出所有 Token / List All Tokens

```
devtoken list
```

**显示内容 / Shows:**
- Token ID
- 备注
- 状态（Active/Revoked）
- 创建时间
- 最后使用时间

#### 3. 撤销 Token / Revoke Token

```
devtoken revoke <token_id>
```

**示例 / Example:**
```
devtoken revoke jt_abc123def456
```

#### 4. 查看 Token 详情 / View Token Details

```
devtoken info <token_id>
```

**显示内容 / Shows:**
- Token ID
- 完整 Token 字符串
- 备注
- 状态
- 创建者
- 创建时间
- 最后使用时间

---

## API 使用 / API Usage

### 认证 / Authentication

所有 API 端点都需要 Bearer Token 认证：

All API endpoints require Bearer Token authentication:

```bash
curl -H "Authorization: Bearer <your_token>" https://your-domain.com/api/v1/...
```

### 可用端点 / Available Endpoints

#### 1. 获取用户信息 / Get User Info

```http
GET /api/v1/user/<user_id>
```

**示例 / Example:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/user/U123456
```

**响应 / Response:**
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

#### 2. 获取用户列表 / Get User List

```http
GET /api/v1/users
```

**示例 / Example:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/users
```

**响应 / Response:**
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


---

## 错误处理 / Error Handling

### 401 Unauthorized

**情况 / Cases:**
- 未提供 Authorization header
- Token 格式错误
- Token 无效或已被撤销

**响应示例 / Response Example:**
```json
{
  "error": "Invalid token",
  "message": "Token is invalid or has been revoked"
}
```

### 404 Not Found

**情况 / Cases:**
- 请求的资源不存在（例如：用户不存在）

**响应示例 / Response Example:**
```json
{
  "error": "User not found",
  "message": "User U123456 does not exist"
}
```

### 500 Internal Server Error

**情况 / Cases:**
- 服务器内部错误

**响应示例 / Response Example:**
```json
{
  "error": "Internal server error",
  "message": "Error description"
}
```

---

## 安全建议 / Security Recommendations

1. **妥善保管 Token / Keep tokens secure**
   - Token 只在创建时显示一次
   - 请将 Token 保存在安全的位置
   - 不要在公共代码库中提交 Token

2. **定期轮换 Token / Rotate tokens regularly**
   - 定期撤销旧 Token 并创建新 Token
   - 为不同的应用使用不同的 Token

3. **使用 HTTPS / Use HTTPS**
   - 始终通过 HTTPS 传输 Token
   - 避免在不安全的网络中使用 API

4. **监控使用情况 / Monitor usage**
   - 定期检查 Token 的最后使用时间
   - 撤销不再使用的 Token

5. **最小权限原则 / Principle of least privilege**
   - 只为需要的应用创建 Token
   - 及时撤销不再需要的访问权限

---

## 技术实现 / Technical Implementation

### 数据存储 / Data Storage

Token 数据存储位置由 `config.json` 中的 `file_path.dev_tokens` 配置项决定（默认：`./data/dev_tokens.json`）：

Token data storage location is configured by `file_path.dev_tokens` in `config.json` (default: `./data/dev_tokens.json`):

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

### 装饰器使用 / Decorator Usage

在新的 API 端点中使用 `@require_dev_token` 装饰器：

Use the `@require_dev_token` decorator for new API endpoints:

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

---

## 示例代码 / Example Code

### Python

```python
import requests

TOKEN = "your_token_here"
BASE_URL = "https://jietng.matsuki.work"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# 获取用户列表
response = requests.get(f"{BASE_URL}/api/v1/users", headers=headers)
users = response.json()

print(f"Total users: {users['count']}")
for user in users['users']:
    print(f"  - {user['nickname']} ({user['user_id']})")
```

### JavaScript

```javascript
const TOKEN = 'your_token_here';
const BASE_URL = 'https://jietng.matsuki.work';

async function getUsers() {
  const response = await fetch(`${BASE_URL}/api/v1/users`, {
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
BASE_URL="https://jietng.matsuki.work"

# 获取用户列表
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/users"

# 获取特定用户信息
USER_ID="U123456"
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/user/$USER_ID"

# 获取 DX 歌曲列表
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/api/v1/songs?type=dx"
```

---

## 常见问题 / FAQ

### Q: Token 会过期吗？
**A:** 目前 Token 不会自动过期，但可以被管理员手动撤销。

### Q: Can tokens expire?
**A:** Currently, tokens do not expire automatically, but can be manually revoked by administrators.

---

### Q: 丢失 Token 怎么办？
**A:** Token 只在创建时显示一次。如果丢失，需要撤销旧 Token 并创建新的。

### Q: What if I lose my token?
**A:** Tokens are only shown once during creation. If lost, you need to revoke the old token and create a new one.

---

### Q: 一个应用可以有多个 Token 吗？
**A:** 可以。建议为不同的用途创建不同的 Token，便于管理和撤销。

### Q: Can one application have multiple tokens?
**A:** Yes. It's recommended to create different tokens for different purposes for easier management and revocation.

---

### Q: Token 的权限范围是什么？
**A:** 所有通过认证的 Token 具有相同的 API 访问权限。目前不支持细粒度的权限控制。

### Q: What are the permission scopes of tokens?
**A:** All authenticated tokens have the same API access permissions. Fine-grained permission control is not currently supported.

---

## 版本历史 / Version History

- **v1.0** (2025-01-24): 初始版本，支持基本的 Token 管理和 API 认证
  - Initial release with basic token management and API authentication

---

## 相关文件 / Related Files

- `config.json` - 配置文件（包含 Token 文件路径）
- `modules/config_loader.py` - 配置加载器
- `modules/devtoken_manager.py` - Token 管理核心逻辑
- `modules/message_manager.py` - 三语消息定义
- `main.py` - API 端点和命令处理
- `data/dev_tokens.json` - Token 数据存储（默认位置）

---

## 支持 / Support

如有问题或建议，请联系系统管理员。

For questions or suggestions, please contact the system administrator.

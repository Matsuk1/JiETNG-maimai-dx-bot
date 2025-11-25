# Developer API Documentation

## Overview

The Developer Token system allows administrators to create and manage API access tokens for third-party applications or scripts to access JiETNG's API endpoints.

---

## Quick Start

### Get API Token

If you want to use the JiETNG API, follow these steps to get an access token:

1. **Send Email**
   - To: `matsuk1@proton.me`
   - Subject: `JiETNG API Token Request`
   - Content:
     - Your name or organization
     - Purpose of use
     - Expected usage frequency

2. **Wait for Review**
   - The administrator will review your application and create a dedicated token

3. **Receive Token**
   - You will receive the Token ID and complete token string via email
   - **Keep your token secure, it will only be shown once!**

### API Base Information

- **Base URL**: `https://jietng.matsuki.top/api/v1/`
- **Authentication**: Bearer Token
- **Request Format**: GET requests with parameters passed via URL query string
- **Response Format**: JSON

### Usage Example

```bash
# Use your token to access the API
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     "https://jietng.matsuki.top/api/v1/users"
```

---

## Features

- ✅ Create secure API tokens (using `secrets.token_urlsafe(32)`)
- ✅ Add notes to each token
- ✅ List all tokens and their status
- ✅ Revoke tokens that are no longer needed
- ✅ View token details
- ✅ Automatically track token last usage time
- ✅ Bearer Token authentication decorator
- ✅ Trilingual support (Japanese/English/Chinese)

---

## Command Usage

### Admin Commands

Only administrators can use the following commands in LINE Bot:

#### 1. Create Token

```
devtoken create <note>
```

**Example:**
```
devtoken create MyApp API Integration
```

**Returns:**
- Token ID (for management)
- Complete token string (keep it secure)
- Note

#### 2. List All Tokens

```
devtoken list
```

**Shows:**
- Token ID
- Note
- Status (Active/Revoked)
- Created at
- Last used

#### 3. Revoke Token

```
devtoken revoke <token_id>
```

**Example:**
```
devtoken revoke jt_abc123def456
```

#### 4. View Token Details

```
devtoken info <token_id>
```

**Shows:**
- Token ID
- Complete token string
- Note
- Status
- Creator
- Created at
- Last used

---

## API Usage

### Base URL

```
https://jietng.matsuki.top/api/v1/
```

### Authentication

All API endpoints require Bearer Token authentication:

```bash
curl -H "Authorization: Bearer <your_token>" https://jietng.matsuki.top/api/v1/...
```

### Available Endpoints

All endpoints below should be prefixed with `https://jietng.matsuki.top/api/v1/`.

#### 1. Get User Info

```http
GET /api/v1/user/<user_id>
```

**Example:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/user/U123456
```

**Response:**
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

#### 2. Get User List

```http
GET /api/v1/users
```

**Example:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/users
```

**Response:**
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

#### 3. Search Songs

```http
GET /api/v1/search?q=<query>&ver=<version>&max_results=<limit>
```

**Parameters:**
- `q`: Search query (optional, defaults to empty string; use `__empty__` for explicit empty string)
- `ver`: Version (jp/intl, optional, defaults to jp)
- `max_results`: Maximum number of results (optional, defaults to 6)

**Example:**
```bash
# Search Japanese songs
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=%E3%83%92%E3%83%90%E3%83%8A&ver=jp"

# Search empty string song names
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=__empty__&ver=jp"
```

**Response:**
```json
{
  "success": true,
  "count": 2,
  "songs": [
    {
      "id": 123,
      "title": "ヒバナ",
      "artist": "Artist Name",
      ...
    }
  ]
}
```

#### 4. Queue User Update

```http
GET /api/v1/update/<user_id>
```

**Example:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/update/U123456
```

**Response:**
```json
{
  "success": true,
  "user_id": "U123456",
  "task_id": "task_xxx",
  "queue_size": 5,
  "message": "User update task queued successfully"
}
```

#### 5. Get User Records

```http
GET /api/v1/records/<user_id>?type=<record_type>&command=<filter>
```

**Parameters:**
- `type`: Record type (best50/best100/best35/best15/allb50/allb35/apb50/rct50/idealb50, optional, defaults to best50)
- `command`: Filter command (optional, supports -ver, -fc, -rate, etc.)

**Example:**
```bash
# Get best50
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/records/U123456?type=best50"

# Filter specific version
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/records/U123456?type=best50&command=-ver%20DX%20FESTiVAL%20PLUS"
```

**Response:**
```json
{
  "success": true,
  "old_songs": [...],
  "new_songs": [...]
}
```

#### 6. Get Version List

```http
GET /api/v1/versions
```

**Example:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/versions
```

**Response:**
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

#### 7. Register User

```http
GET /api/v1/register/<user_id>?nickname=<name>&language=<lang>
```

**Parameters:**
- `nickname`: **Required**, user nickname (automatically fetched from LINE API for LINE users, otherwise use this parameter)
- `language`: Language setting (ja/en/zh, optional, defaults to en)

**Requirements:**
- `user_id` must start with `U` (LINE user ID format)

**Nickname Priority:**
1. Automatically fetch from LINE API (if LINE user)
2. Get from user data's nickname field
3. Use the provided nickname parameter

**Example:**
```bash
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/register/U123456?nickname=TestUser&language=en"
```

**Response:**
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

**Registration Tracking:**

New users registered via API will automatically track:
- `registered_via_token`: The token ID used for registration
- `registered_at`: Registration timestamp (format: YYYY-MM-DD HH:MM:SS)

---

## Error Handling

### 401 Unauthorized

**Cases:**
- Missing Authorization header
- Invalid token format
- Token is invalid or has been revoked

**Response Example:**
```json
{
  "error": "Invalid token",
  "message": "Token is invalid or has been revoked"
}
```

### 400 Bad Request

**Cases:**
- Missing required parameters (e.g., register endpoint missing nickname)
- Invalid parameter values (e.g., language not in allowed list)
- Invalid user_id format (e.g., register endpoint user_id doesn't start with 'U')

**Response Example:**
```json
{
  "error": "Missing parameter",
  "message": "Parameter 'nickname' is required"
}
```

```json
{
  "error": "Invalid user_id",
  "message": "user_id must start with 'U'"
}
```

### 404 Not Found

**Cases:**
- Requested resource does not exist (e.g., user not found)

**Response Example:**
```json
{
  "error": "User not found",
  "message": "User U123456 does not exist"
}
```

### 500 Internal Server Error

**Cases:**
- Internal server error

**Response Example:**
```json
{
  "error": "Internal server error",
  "message": "Error description"
}
```

---

## API Endpoints Summary

| Endpoint | Method | Description |
|----------------|--------------|-------------------|
| `/user/<user_id>` | GET | Get user info |
| `/users` | GET | Get all users |
| `/search` | GET | Search songs |
| `/update/<user_id>` | GET | Queue user update |
| `/records/<user_id>` | GET | Get user records |
| `/versions` | GET | Get version list |
| `/register/<user_id>` | GET | Register user and generate bind URL |

---

## Security Recommendations

1. **Keep tokens secure**
   - Tokens are only shown once during creation
   - Store tokens in a secure location
   - Don't commit tokens to public repositories

2. **Rotate tokens regularly**
   - Periodically revoke old tokens and create new ones
   - Use different tokens for different applications

3. **Use HTTPS**
   - Always transmit tokens over HTTPS
   - Avoid using the API on unsecured networks

4. **Monitor usage**
   - Regularly check token last usage times
   - Revoke unused tokens

5. **Principle of least privilege**
   - Only create tokens for necessary applications
   - Revoke access permissions promptly when no longer needed

---

## Technical Implementation

### Data Storage

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

### Decorator Usage

Use the `@require_dev_token` decorator for new API endpoints:

```python
@app.route("/api/v1/my_endpoint", methods=["GET"])
@csrf.exempt
@require_dev_token
def my_api_endpoint():
    # Token info is automatically added to request.token_info
    token_info = request.token_info
    logger.info(f"API access via token {token_info['token_id']}")

    return jsonify({"success": True})
```

---

## Example Code

### Python

```python
import requests

TOKEN = "your_token_here"
BASE_URL = "https://jietng.matsuki.top/api/v1"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Get user list
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

# Get user list
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/users"

# Get specific user info
USER_ID="U123456"
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/user/$USER_ID"

# Search songs
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/search?q=ヒバナ&ver=jp"
```

---

## FAQ

### Q: Can tokens expire?
**A:** Currently, tokens do not expire automatically, but can be manually revoked by administrators.

### Q: What if I lose my token?
**A:** Tokens are only shown once during creation. If lost, you need to revoke the old token and create a new one.

### Q: Can one application have multiple tokens?
**A:** Yes. It's recommended to create different tokens for different purposes for easier management and revocation.

### Q: What are the permission scopes of tokens?
**A:** All authenticated tokens have the same API access permissions. Fine-grained permission control is not currently supported.

---

## Version History

- **v1.0** (2025-01-24): Initial release with basic token management and API authentication

---

## Related Files

- `config.json` - Configuration file (contains token file path)
- `modules/config_loader.py` - Configuration loader
- `modules/devtoken_manager.py` - Token management core logic
- `modules/message_manager.py` - Trilingual message definitions
- `main.py` - API endpoints and command handling
- `data/dev_tokens.json` - Token data storage (default location)

---

## Support

For questions or suggestions, please contact the system administrator (email: matsuk1@proton.me).

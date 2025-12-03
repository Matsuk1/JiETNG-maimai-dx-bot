# Developer API Documentation

## Overview

The Developer Token system allows administrators to create and manage API access tokens for third-party applications or scripts to access JiETNG's API endpoints.


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
   - **Keep your token secure!**

### API Base Information

- **Base URL**: `https://jietng.matsuki.top/api/v1/`
- **Authentication**: Bearer Token
- **Response Format**: JSON

### Usage Example

```bash
# Use your token to access the API
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     "https://jietng.matsuki.top/api/v1/users"
```


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

#### 1. Get User List

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

#### 2. Register User

```http
POST /api/v1/register/<user_id>
```

**Request Body (JSON):**
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
curl -X POST -H "Authorization: Bearer abc123..." -H "Content-Type: application/json" -d '{"nickname":"TestUser","language":"en"}' https://jietng.matsuki.top/api/v1/register/U123456
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

#### 3. Get User Info

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

#### 4. Delete User

```http
DELETE /api/v1/user/<user_id>
```

**Example:**
```bash
curl -X DELETE -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/user/U123456
```

**Response:**
```json
{
  "success": true,
  "user_id": "U123456",
  "message": "User U123456 has been deleted successfully"
}
```

#### 5. Queue User Update

```http
POST /api/v1/update/<user_id>
```

**Example:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/update/U123456
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

#### 6. Query Task Status

```http
GET /api/v1/task/<task_id>
```

**Description:**
Query the status of an update task created via `/update/<user_id>`.

**Example:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/task/task_xxx
```

**Response:**

**Task in progress:**
```json
{
  "success": true,
  "task_id": "task_xxx",
  "status": "pending",
  "message": "Task is still in queue or processing"
}
```

**Task completed:**
```json
{
  "success": true,
  "task_id": "task_xxx",
  "status": "completed",
  "result": {
    // Result data from the update task
  }
}
```

**Task not found or expired:**
```json
{
  "success": false,
  "task_id": "task_xxx",
  "status": "not_found",
  "message": "Task not found or has expired"
}
```

#### 7. Get User Records

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

#### 8. Search Songs

```http
GET /api/v1/search?q=<query>&user_id=<user_id>&ver=<version>&max_results=<limit>
```

**Parameters:**
- `q`: Search query (optional, defaults to empty string; use `__empty__` for explicit empty string)
- `user_id`: Match songs in the specified user's score database (default is empty, no matching)
- `ver`: Version (jp/intl, optional, defaults to jp, after specifying the user_id, this field can be omitted.)
- `max_results`: Maximum number of results (optional, defaults to 6)

**Example:**
```bash
# Search Japanese songs
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=%E3%83%92%E3%83%90%E3%83%8A&ver=jp"

# Search empty string song names
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=__empty__&ver=jp"

# Match within the user's score database
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=%E3%83%92%E3%83%90%E3%83%8A&user_id=U123456"
```

**Response:**
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

#### 9. Get Version List

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

## Permission Request API

The permission request system allows developer tokens to request access to user data not created by that token. Users can approve or reject these requests.

### Permission Model

JiETNG uses a two-tier permission model:

1. **Owner Permission**: The token that created the user (identified by `registered_via_token` field)
   - Can perform all operations: read, update, delete user
   - Can manage permission requests: view, approve, reject, revoke

2. **Granted Access Permission**: Tokens authorized by the user (in token's `allowed_users` list)
   - Can read user data
   - Can trigger user data updates
   - **Cannot** delete users or manage permissions

### Decorator Description

The API uses two decorators to control access permissions:

- **`@require_user_permission`**: Allows both owners and authorized tokens (for read operations)
- **`@require_owner_permission`**: Only allows owners (for sensitive operations)

#### 10. Request Access Permission

```http
POST /api/v1/perm/<user_id>
```

**Description:** Send a permission request to access the specified user's data.

**Permission Required:** Any valid developer token

**Request Body (JSON):**
- `requester_name`: Optional, requester name (displayed in notifications, defaults to token note)

**Example:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"requester_name":"MyApp"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456
```

**Response:**
```json
{
  "success": true,
  "request_id": "20250203120000_jt_abc123",
  "user_id": "U123456",
  "message": "Permission request sent to user U123456"
}
```

**Error Responses:**
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

#### 11. View Permission Requests

```http
GET /api/v1/perm/<user_id>/requests
```

**Description:** Get the list of pending permission requests for a user.

**Permission Required:** Owner token only (`@require_owner_permission`)

**Example:**
```bash
curl -H "Authorization: Bearer abc123..." \
     https://jietng.matsuki.top/api/v1/perm/U123456/requests
```

**Response:**
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
    }
  ]
}
```

#### 12. Approve Permission Request

```http
POST /api/v1/perm/<user_id>/accept
```

**Description:** Approve the specified permission request, adding the requesting token to the authorized list.

**Permission Required:** Owner token only (`@require_owner_permission`)

**Request Body (JSON):**
- `request_id`: **Required**, the permission request ID to approve

**Example:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"request_id":"20250203120000_jt_abc123"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/accept
```

**Response:**
```json
{
  "success": true,
  "user_id": "U123456",
  "token_id": "jt_abc123",
  "token_note": "MyApp",
  "message": "Permission granted to token jt_abc123"
}
```

#### 13. Reject Permission Request

```http
POST /api/v1/perm/<user_id>/reject
```

**Description:** Reject the specified permission request.

**Permission Required:** Owner token only (`@require_owner_permission`)

**Request Body (JSON):**
- `request_id`: **Required**, the permission request ID to reject

**Example:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"request_id":"20250203120000_jt_abc123"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/reject
```

**Response:**
```json
{
  "success": true,
  "user_id": "U123456",
  "token_id": "jt_abc123",
  "token_note": "MyApp",
  "message": "Permission request from token jt_abc123 rejected"
}
```

#### 14. Revoke Granted Permission

```http
POST /api/v1/perm/<user_id>/revoke
```

**Description:** Revoke access permission previously granted to a specific token.

**Permission Required:** Owner token only (`@require_owner_permission`)

**Request Body (JSON):**
- `token_id`: **Required**, the token ID whose permission to revoke

**Example:**
```bash
curl -X POST -H "Authorization: Bearer abc123..." \
     -H "Content-Type: application/json" \
     -d '{"token_id":"jt_abc123"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/revoke
```

**Response:**
```json
{
  "success": true,
  "user_id": "U123456",
  "token_id": "jt_abc123",
  "message": "Permission revoked for token jt_abc123"
}
```

### Permission Request Workflow Example

```bash
# 1. Token B requests access to User1 created by Token A
curl -X POST -H "Authorization: Bearer TOKEN_B" \
     -H "Content-Type: application/json" \
     -d '{"requester_name":"MyApp"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456

# 2. Token A (owner) views pending requests
curl -H "Authorization: Bearer TOKEN_A" \
     https://jietng.matsuki.top/api/v1/perm/U123456/requests

# 3. Token A approves the request
curl -X POST -H "Authorization: Bearer TOKEN_A" \
     -H "Content-Type: application/json" \
     -d '{"request_id":"20250203120000_jt_tokenb"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/accept

# 4. Now Token B can access User1's data
curl -H "Authorization: Bearer TOKEN_B" \
     https://jietng.matsuki.top/api/v1/user/U123456

# 5. (Optional) Token A revokes Token B's access
curl -X POST -H "Authorization: Bearer TOKEN_A" \
     -H "Content-Type: application/json" \
     -d '{"token_id":"jt_tokenb"}' \
     https://jietng.matsuki.top/api/v1/perm/U123456/revoke
```

### LINE User Permission Management

LINE users receive FlexMessage notifications for permission requests and can approve or reject directly in LINE:

1. When a new permission request arrives, users receive a notification message
2. The message includes requester information and two buttons: "Accept" and "Reject"
3. Clicking a button automatically processes the request

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

### 403 Forbidden

**Cases:**
- The current token cannot access this user_id
- Token is not the user's owner (for operations requiring owner permission)
- Token is neither the owner nor authorized

**Response Examples:**
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


## API Endpoints Summary

### Basic Endpoints

| Endpoint | Method | Description | Permission Required |
|----------------|--------------|-------------------|----------|
| `/users` | GET | Get all users | Any Token |
| `/register/<user_id>` | POST | Register user and generate bind URL | Any Token |
| `/user/<user_id>` | GET | Get user info | Owner or Granted |
| `/user/<user_id>` | DELETE | Delete user | **Owner Only** |
| `/update/<user_id>` | POST | Queue user update | Owner or Granted |
| `/task/<task_id>` | GET | Query task status | Any Token |
| `/records/<user_id>` | GET | Get user records | Owner or Granted |
| `/search` | GET | Search songs | Any Token |
| `/versions` | GET | Get version list | Any Token |

### Permission Management Endpoints

| Endpoint | Method | Description | Permission Required |
|----------------|--------------|-------------------|----------|
| `/perm/<user_id>` | POST | Request access permission | Any Token |
| `/perm/<user_id>/requests` | GET | View permission requests | **Owner Only** |
| `/perm/<user_id>/accept` | POST | Approve permission request | **Owner Only** |
| `/perm/<user_id>/reject` | POST | Reject permission request | **Owner Only** |
| `/perm/<user_id>/revoke` | POST | Revoke granted permission | **Owner Only** |

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


## FAQ

### Q: Can tokens expire?
**A:** Currently, tokens do not expire automatically, but can be manually revoked by administrators.

### Q: What if I lose my token?
**A:** Tokens are only shown once during creation. If lost, you need to revoke the old token and create a new one.

### Q: Can one application have multiple tokens?
**A:** Yes. It's recommended to create different tokens for different purposes for easier management and revocation.

### Q: What are the permission scopes of tokens?
**A:** All authenticated tokens have the same API access permissions. Fine-grained permission control is not currently supported.


## Version History

- **v1.1** (2025-02-03): Added permission request system
  - Added 5 permission management API endpoints
  - Implemented two-tier permission model (owner vs granted)
  - Added `@require_owner_permission` decorator
  - LINE users receive FlexMessage notifications for permission requests
- **v1.0** (2025-01-24): Initial release with basic token management and API authentication


## Related Files

- `config.json` - Configuration file (contains token file path)
- `modules/config_loader.py` - Configuration loader
- `modules/devtoken_manager.py` - Token management core logic
- `modules/perm_request_handler.py` - Permission request handling logic
- `modules/perm_request_generator.py` - Permission request FlexMessage generator
- `modules/message_manager.py` - Trilingual message definitions
- `main.py` - API endpoints and command handling
- `data/dev_tokens.json` - Token data storage (default location)


## Support

For questions or suggestions, please contact the system administrator (email: matsuk1@proton.me).

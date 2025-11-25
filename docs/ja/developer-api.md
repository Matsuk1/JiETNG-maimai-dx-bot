# 開発者 API ドキュメント

## 概要

開発者トークンシステムにより、管理者は第三者アプリケーションやスクリプトがJiETNGのAPIエンドポイントにアクセスするためのAPIアクセストークンを作成・管理できます。

## クイックスタート

### API トークンの取得

JiETNG APIを使用したい場合は、以下の手順でアクセストークンを取得してください:

1. **メールを送信**
   - 宛先: `matsuk1@proton.me`
   - 件名: `JiETNG API Token Request`
   - 内容:
     - お名前または組織名
     - 使用目的の説明
     - 予想される使用頻度

2. **審査を待つ**
   - 管理者があなたの申請を審査し、専用トークンを作成します

3. **トークンを受け取る**
   - メールでトークンIDと完全なトークン文字列を受け取ります
   - **トークンを安全に保管してください！**

### API 基本情報

- **Base URL**: `https://jietng.matsuki.top/api/v1/`
- **認証方式**: Bearer Token
- **リクエスト形式**: GETリクエスト、パラメータはURL query stringで渡す
- **レスポンス形式**: JSON

### 使用例

```bash
# トークンを使用してAPIにアクセス
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     "https://jietng.matsuki.top/api/v1/users"
```

## コマンド使用法

### 管理者コマンド

以下のコマンドはLINE Botで管理者のみが使用できます:

#### 1. トークン作成

```
devtoken create <メモ>
```

**例:**
```
devtoken create MyApp API Integration
```

**返り値:**
- トークンID（管理用）
- 完全なトークン文字列（安全に保管してください）
- メモ

#### 2. すべてのトークンを一覧表示

```
devtoken list
```

**表示内容:**
- トークンID
- メモ
- 状態（Active/Revoked）
- 作成日時
- 最終使用日時

#### 3. トークン無効化

```
devtoken revoke <token_id>
```

**例:**
```
devtoken revoke jt_abc123def456
```

#### 4. トークン詳細表示

```
devtoken info <token_id>
```

**表示内容:**
- トークンID
- 完全なトークン文字列
- メモ
- 状態
- 作成者
- 作成日時
- 最終使用日時

## API 使用法

### Base URL

```
https://jietng.matsuki.top/api/v1/
```

### 認証

すべてのAPIエンドポイントはBearer Token認証が必要です:

```bash
curl -H "Authorization: Bearer <your_token>" https://jietng.matsuki.top/api/v1/...
```

### 利用可能なエンドポイント

以下のすべてのエンドポイントは `https://jietng.matsuki.top/api/v1/` をプレフィックスとして使用します。

#### 1. ユーザー情報取得

```http
GET /api/v1/user/<user_id>
```

**例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/user/U123456
```

**レスポンス:**
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

#### 2. ユーザー一覧取得

```http
GET /api/v1/users
```

**例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/users
```

**レスポンス:**
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

#### 3. 楽曲検索

```http
GET /api/v1/search?q=<query>&ver=<version>&max_results=<limit>
```

**パラメータ:**
- `q`: 検索キーワード（オプション、デフォルトは空文字列；明示的な空文字列には `__empty__` を使用）
- `ver`: バージョン (jp/intl、オプション、デフォルトはjp)
- `max_results`: 最大結果数（オプション、デフォルトは6）

**例:**
```bash
# 日本語楽曲を検索
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=%E3%83%92%E3%83%90%E3%83%8A&ver=jp"

# 空文字列の曲名を検索
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/search?q=__empty__&ver=jp"
```

**レスポンス:**
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

#### 4. ユーザー更新キュー

```http
GET /api/v1/update/<user_id>
```

**例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/update/U123456
```

**レスポンス:**
```json
{
  "success": true,
  "user_id": "U123456",
  "task_id": "task_xxx",
  "queue_size": 5,
  "message": "User update task queued successfully"
}
```

#### 5. ユーザーレコード取得

```http
GET /api/v1/records/<user_id>?type=<record_type>&command=<filter>
```

**パラメータ:**
- `type`: レコードタイプ (best50/best100/best35/best15/allb50/allb35/apb50/rct50/idealb50、オプション、デフォルトはbest50)
- `command`: フィルターコマンド（オプション、-ver、-fc、-rate などをサポート）

**例:**
```bash
# best50を取得
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/records/U123456?type=best50"

# 特定のバージョンでフィルター
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/records/U123456?type=best50&command=-ver%20DX%20FESTiVAL%20PLUS"
```

**レスポンス:**
```json
{
  "success": true,
  "old_songs": [...],
  "new_songs": [...]
}
```

#### 6. バージョン一覧取得

```http
GET /api/v1/versions
```

**例:**
```bash
curl -H "Authorization: Bearer abc123..." https://jietng.matsuki.top/api/v1/versions
```

**レスポンス:**
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

#### 7. ユーザー登録

```http
GET /api/v1/register/<user_id>?nickname=<name>&language=<lang>
```

**パラメータ:**
- `nickname`: **必須**、ユーザーのニックネーム（LINEユーザーの場合はLINE APIから自動取得、それ以外の場合はこのパラメータを使用）
- `language`: 言語設定 (ja/en/zh、オプション、デフォルトはen)

**要件:**
- `user_id` は `U` で始まる必要があります（LINE ユーザーID形式）

**ニックネーム取得の優先順位:**
1. LINE APIから自動取得（LINEユーザーの場合）
2. ユーザーデータのnicknameフィールドから取得
3. 提供されたnicknameパラメータを使用

**例:**
```bash
curl -H "Authorization: Bearer abc123..." "https://jietng.matsuki.top/api/v1/register/U123456?nickname=TestUser&language=en"
```

**レスポンス:**
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

**登録記録:**

API経由で登録された新規ユーザーは以下の情報を自動的に記録します:
- `registered_via_token`: 登録時に使用されたトークンID
- `registered_at`: 登録タイムスタンプ（形式: YYYY-MM-DD HH:MM:SS）

## エラー処理

### 401 Unauthorized

**ケース:**
- Authorization ヘッダーが提供されていない
- トークン形式が無効
- トークンが無効または無効化されている

**レスポンス例:**
```json
{
  "error": "Invalid token",
  "message": "Token is invalid or has been revoked"
}
```

### 400 Bad Request

**ケース:**
- 必須パラメータが不足（例: registerエンドポイントでnicknameが欠けている）
- パラメータ値が無効（例: languageが許可リストにない）
- user_id形式が無効（例: registerエンドポイントのuser_idが'U'で始まらない）

**レスポンス例:**
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

**ケース:**
- リクエストされたリソースが存在しない（例: ユーザーが見つからない）

**レスポンス例:**
```json
{
  "error": "User not found",
  "message": "User U123456 does not exist"
}
```

### 500 Internal Server Error

**ケース:**
- サーバー内部エラー

**レスポンス例:**
```json
{
  "error": "Internal server error",
  "message": "Error description"
}
```

## API エンドポイント一覧

| エンドポイント | メソッド | 説明 |
|----------------|--------------|-------------------|
| `/user/<user_id>` | GET | ユーザー情報を取得 |
| `/users` | GET | すべてのユーザーを取得 |
| `/search` | GET | 楽曲を検索 |
| `/update/<user_id>` | GET | ユーザー更新をキュー |
| `/records/<user_id>` | GET | ユーザーレコードを取得 |
| `/versions` | GET | バージョン一覧を取得 |
| `/register/<user_id>` | GET | ユーザーを登録し連携URLを生成 |

## セキュリティ推奨事項

1. **トークンを安全に保管**
   - トークンは作成時に一度しか表示されません
   - トークンを安全な場所に保存してください
   - 公開リポジトリにトークンをコミットしないでください

2. **定期的にトークンをローテーション**
   - 定期的に古いトークンを無効化し、新しいトークンを作成してください
   - 異なるアプリケーションには異なるトークンを使用してください

3. **HTTPS を使用**
   - 常にHTTPS経由でトークンを送信してください
   - 安全でないネットワークでAPIを使用しないでください

4. **使用状況を監視**
   - 定期的にトークンの最終使用時刻を確認してください
   - 使用されていないトークンを無効化してください

5. **最小権限の原則**
   - 必要なアプリケーションにのみトークンを作成してください
   - 不要になったアクセス権限は速やかに無効化してください

## 技術実装

### データストレージ

トークンデータの保存場所は `config.json` の `file_path.dev_tokens` で設定されます（デフォルト: `./data/dev_tokens.json`）:

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

### デコレーター使用法

新しいAPIエンドポイントには `@require_dev_token` デコレーターを使用します:

```python
@app.route("/api/v1/my_endpoint", methods=["GET"])
@csrf.exempt
@require_dev_token
def my_api_endpoint():
    # トークン情報は request.token_info に自動的に追加されます
    token_info = request.token_info
    logger.info(f"API access via token {token_info['token_id']}")

    return jsonify({"success": True})
```

## サンプルコード

### Python

```python
import requests

TOKEN = "your_token_here"
BASE_URL = "https://jietng.matsuki.top/api/v1"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# ユーザー一覧を取得
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

# ユーザー一覧を取得
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/users"

# 特定のユーザー情報を取得
USER_ID="U123456"
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/user/$USER_ID"

# 楽曲を検索
curl -H "Authorization: Bearer $TOKEN" "$BASE_URL/search?q=ヒバナ&ver=jp"
```

## よくある質問

### Q: トークンは期限切れになりますか？
**A:** 現在、トークンは自動的に期限切れになりませんが、管理者が手動で無効化できます。

### Q: トークンを紛失した場合はどうすればよいですか？
**A:** トークンは作成時に一度しか表示されません。紛失した場合は、古いトークンを無効化し、新しいトークンを作成する必要があります。

### Q: 1つのアプリケーションで複数のトークンを持つことはできますか？
**A:** はい。管理と無効化を容易にするため、異なる目的には異なるトークンを作成することをお勧めします。

### Q: トークンの権限範囲はどうなっていますか？
**A:** 認証されたすべてのトークンは同じAPIアクセス権限を持っています。現在、細かい権限制御はサポートされていません。

## バージョン履歴

- **v1.0** (2025-01-24): 基本的なトークン管理とAPI認証をサポートする初回リリース

## 関連ファイル

- `config.json` - 設定ファイル（トークンファイルパスを含む）
- `modules/config_loader.py` - 設定ローダー
- `modules/devtoken_manager.py` - トークン管理のコアロジック
- `modules/message_manager.py` - 三ヶ国語メッセージ定義
- `main.py` - APIエンドポイントとコマンド処理
- `data/dev_tokens.json` - トークンデータストレージ（デフォルト位置）

## サポート

質問や提案がある場合は、システム管理者にお問い合わせください（メール: matsuk1@proton.me）。

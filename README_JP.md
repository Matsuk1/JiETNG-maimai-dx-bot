# JiETNG - LINE Bot

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="100" />

**Maimai DX スコア追跡とデータ管理システム**

日本版と海外版に対応

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.14.5-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

[简体中文](README.md) | [English](README_EN.md) | 日本語

[機能](#機能) • [コマンドリスト](COMMANDS_JP.md) • [オンラインドキュメント](https://jietng.matsuki.work/ja/) • [クイックスタート](#クイックスタート) • [管理パネル](#管理パネル) • [デプロイガイド](#デプロイガイド) • [開発ドキュメント](#開発ドキュメント)

</div>

---

## プロジェクト概要

**JiETNG** は、Maimai DX プレイヤー向けの包括的な LINE Bot サービスで、スコア追跡、データ分析、およびさまざまなゲーム補助機能を提供します。日本版（JP）と海外版（INTL）の両方に対応しています。

### コア機能

- **スコア追跡**: Best/Recent ゲーム記録の自動同期と保存
- **データ可視化**: 詳細な B50/B100 スコアチャート生成、カスタムフィルター対応
- **フレンドシステム**: フレンドスコアの閲覧、フレンド申請管理
- **バージョン進捗**: 各バージョンの達成状況追跡（極/将/神/舞舞）
- **楽曲推薦**: 難易度定数によるランダム楽曲推薦
- **位置情報サービス**: 近くの Maimai 設置店舗を検索
- **データセキュリティ**: SEGA アカウント情報を Fernet 暗号化で保存
- **管理パネル**: 完全な Web 管理インターフェース
- **パフォーマンス最適化**: デュアルキューアーキテクチャ（画像キュー/ネットワークキュー）と頻度制限
- **多言語対応**: 日本語/英語/中国語インターフェース、多言語ドキュメント

---

## 機能

### 主要機能

- **アカウント管理**: SEGA アカウント連携、表示、連携解除
- **スコア照会**: B50/B100/B35/B15/AB50/AP50/RCT50/IDEALB50 など多種類のスコア図
- **高度なフィルター**: 譜面定数、Rating、達成率、DX スコアなど複数条件の組み合わせフィルター
- **楽曲検索**: 楽曲情報検索、個人スコア照会、ランダム選曲
- **バージョン達成**: 極/将/神/舞舞称号の達成状況追跡
- **フレンド機能**: フレンドリスト、フレンド B50 閲覧
- **ユーティリティ**: Rating 計算、スコア計算機
- **位置情報サービス**: 位置情報送信で近くの Maimai 設置店舗を検索

### 📖 完全コマンドリスト

詳細なコマンド説明と使用例は **[COMMANDS_JP.md](COMMANDS_JP.md)** をご覧ください

---

## 管理パネル

Web ベースの管理インターフェースで、包括的なユーザーとシステム管理機能を提供します。

### アクセス URL

```
https://your-domain.com/linebot/admin
```

### 機能モジュール

| モジュール | 説明 |
|-----------|------|
| **ユーザー管理** | 全ユーザー表示、ユーザーデータ編集、ユーザー削除、更新トリガー |
| **リアルタイムニックネーム** | LINE SDK から自動取得しキャッシュ（5分間キャッシュ） |
| **デュアルキュー監視** | 画像キュー（3並列）+ ネットワークキュー（1並列） |
| **タスク追跡** | 最近 20 件の完了タスクと実行時間統計を表示 |
| **頻度制限** | 30秒以内の重複リクエストを防止（各タスクタイプ最大2件） |
| **システム統計** | ユーザー数、バージョン分布、CPU/メモリ使用率、キュー状態、稼働時間 |
| **リアルタイムログ** | 最近 100 行のログ表示、ANSI カラーコード対応 |
| **データリフレッシュ** | 個別ユーザーデータとニックネームの高速リフレッシュ |

### 主な特徴

- **遅延読み込み**: ログイン後すぐにページ表示、ニックネームは非同期読み込み
- **レスポンシブデザイン**: デスクトップとモバイルデバイスに完全対応
- **デュアルキューアーキテクチャ**: 画像生成とネットワークタスクを分離し、並列性能を向上
- **タスク追跡**: 実行中/待機中/完了タスクと所要時間統計をリアルタイム表示
- **スマート制限**: 高速な重複リクエストからサーバーリソースを保護
- **カラーログ**: ANSI カラーコード対応で、エラー/警告を識別しやすく
- **セッション管理**: Cookie ベースの安全な認証
- **状態維持**: ページリフレッシュ後も現在のタブ状態を維持

### 設定方法

`config.json` に管理者パスワードを追加：

```json
{
    "admin_password": "your_secure_password"
}
```

### 使用方法

1. `https://your-domain.com/linebot/admin` にアクセス
2. 管理者パスワードでログイン
3. 5つの主要タブでナビゲーション：
   - **Users**: ユーザーリストとデータ管理
   - **Task Queue**: デュアルキュー監視（画像 + ネットワークキュー）
   - **Statistics**: システム統計情報
   - **Notices**: お知らせ管理
   - **Logs**: リアルタイムログビューア

---

## クイックスタート

### システム要件

- **Python**: 3.8 以上
- **MySQL**: 5.7+ / MariaDB 10.2+
- **OS**: Linux / macOS / Windows

### インストール手順

#### 1. リポジトリをクローン

```bash
git clone https://github.com/Matsuk1/JiETNG.git
cd JiETNG
```

#### 2. 依存関係をインストール

```bash
pip install -r requirements.txt
```

#### 3. データベースを設定

```bash
# MySQL にログイン
mysql -u root -p

# データベースとユーザーを作成
CREATE DATABASE records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jietng'@'localhost' IDENTIFIED BY 'jietng_2025';
GRANT ALL PRIVILEGES ON records.* TO 'jietng'@'localhost';
FLUSH PRIVILEGES;

# データベース構造をインポート
mysql -u jietng -p records < records_db.sql
```

#### 4. config.json を設定

`config.json` ファイルを編集：

```json
{
    "admin_id": ["U0123456789abcdef"],
    "admin_password": "your_admin_password",
    "domain": "your-domain.com",
    "port": 5100,
    "line_channel": {
        "account_id": "@yourlineid",
        "access_token": "YOUR_CHANNEL_ACCESS_TOKEN",
        "secret": "YOUR_CHANNEL_SECRET"
    },
    "record_database": {
        "host": "localhost",
        "user": "jietng",
        "password": "jietng_2025",
        "database": "records"
    },
    "urls": {
        "line_adding": "https://line.me/R/ti/p/@yourlineid",
        "support_page": "https://github.com/Matsuk1/JiETNG/blob/main/COMMANDS.md",
        "dxdata": [
            "https://raw.githubusercontent.com/gekichumai/dxrating/refs/heads/main/packages/dxdata/dxdata.json",
            "https://dp4p6x0xfi5o9.cloudfront.net/maimai/data.json"
        ]
    }
}
```

#### 5. LINE Channel 認証情報を取得

1. [LINE Developers Console](https://developers.line.biz/) にアクセス
2. Messaging API Channel を作成
3. **Channel Access Token** と **Channel Secret** を取得
4. Webhook URL を設定：`https://your-domain.com/linebot/webhook`
5. **Use webhook** を有効化

#### 6. サービスを起動

```bash
python main.py
```

サービスは `http://0.0.0.0:5100` で起動します

### 本番環境デプロイ（推奨）

```bash
gunicorn -w 4 -b 0.0.0.0:5100 --timeout 120 main:app
```

---

## デプロイガイド

### Docker を使用（推奨）

#### Dockerfile を作成

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# システム依存関係をインストール
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクトファイルをコピー
COPY . .

# ポートを公開
EXPOSE 5100

# 起動コマンド
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5100", "--timeout", "120", "main:app"]
```

#### docker-compose.yml を作成

```yaml
version: '3.8'

services:
  jietng:
    build: .
    container_name: jietng_bot
    ports:
      - "5100:5100"
    volumes:
      - ./data:/app/data
      - ./config.json:/app/config.json
    environment:
      - TZ=Asia/Tokyo
    restart: unless-stopped
    depends_on:
      - mysql

  mysql:
    image: mysql:8.0
    container_name: jietng_mysql
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: records
      MYSQL_USER: jietng
      MYSQL_PASSWORD: jietng_2025
    volumes:
      - mysql_data:/var/lib/mysql
      - ./records_db.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

volumes:
  mysql_data:
```

#### コンテナを起動

```bash
docker-compose up -d
```

### Systemd を使用（Linux）

`/etc/systemd/system/jietng.service` を作成：

```ini
[Unit]
Description=JiETNG Maimai LINE Bot
After=network.target mysql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/jietng
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

サービスを有効化して起動：

```bash
sudo systemctl daemon-reload
sudo systemctl enable jietng
sudo systemctl start jietng
```

### Nginx リバースプロキシを使用

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /linebot {
        proxy_pass http://127.0.0.1:5100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # LINE Webhook 設定
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

HTTPS を有効化（推奨）：

```bash
sudo certbot --nginx -d your-domain.com
```

---

## 開発ドキュメント

### プロジェクト構造

```
JiETNG/
├── main.py                    # Flask アプリケーションエントリーポイント
├── config.json                # 設定ファイル
├── README.md                  # 中国語ドキュメント
├── README_EN.md               # 英語ドキュメント
├── README_JP.md               # 日本語ドキュメント（このファイル）
├── COMMANDS.md                # コマンドリスト（中国語）
├── COMMANDS_EN.md             # コマンドリスト（英語）
├── COMMANDS_JP.md             # コマンドリスト（日本語）
├── requirements.txt           # Python 依存関係
├── records_db.sql             # データベーススキーマ
├── modules/                   # 機能モジュール
│   ├── config_loader.py       # 設定ローダー
│   ├── dbpool_manager.py      # データベース接続プール
│   ├── devtoken_manager.py    # 開発者トークン管理
│   ├── user_manager.py        # ユーザー管理 + ニックネームキャッシュ
│   ├── maimai_manager.py      # Maimai API インターフェース
│   ├── record_manager.py      # データベース操作
│   ├── record_generator.py    # スコアチャート生成
│   ├── song_generator.py      # 楽曲チャート生成
│   ├── image_manager.py       # 画像処理
│   ├── image_cache.py         # 画像キャッシュ
│   ├── image_matcher.py       # 画像認識（カバーマッチング、ハッシュ+SIFT特徴点対応）
│   ├── image_uploader.py      # 画像アップロード（Imgur/uguu/0x0）
│   ├── bindtoken_manager.py   # バインドトークン管理
│   ├── friendlist_generator.py # フレンドリスト生成（Flex Message）
│   ├── notice_manager.py      # お知らせシステム
│   ├── dxdata_manager.py      # 楽曲データ管理
│   ├── json_encrypt.py        # 暗号化ツール
│   ├── rate_limiter.py        # 頻度制限 + リクエスト追跡
│   ├── line_messenger.py      # LINE メッセージ送信
│   ├── song_matcher.py        # 楽曲検索（あいまい一致対応）
│   ├── memory_manager.py      # メモリ管理とクリーンアップ
│   ├── system_checker.py      # システム自己診断
│   ├── storelist_generator.py # 設置店舗リスト生成（Flex Message）
│   ├── friend_request_generator.py # フレンド申請生成（Flex Message）
│   ├── friend_request_handler.py  # フレンド申請処理
│   └── message_manager.py     # 多言語メッセージ管理（お知らせと Tips 含む）
├── templates/                 # HTML テンプレート
│   ├── bind_form.html         # アカウント連携フォーム
│   ├── success.html           # 成功ページ
│   ├── error.html             # エラーページ
│   ├── admin_login.html       # 管理者ログインページ
│   ├── admin_panel.html       # 管理パネルインターフェース
│   └── stats.html             # 統計情報ページ
├── data/                      # データファイル
│   ├── dxdata.json            # 楽曲データベース
│   ├── notice.json            # お知らせ情報
│   ├── re_dxdata.csv          # 地域データ
│   └── user.json.enc          # ユーザーデータ（暗号化）
└── assets/                    # 静的リソース
    ├── fonts/                 # フォントファイル
    ├── pics/                  # 画像
    └── icon/                  # アイコンリソース
```

### データベース構造

#### best_records テーブル

```sql
CREATE TABLE best_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64),
    name VARCHAR(255),
    difficulty VARCHAR(20),
    type VARCHAR(10),
    score VARCHAR(20),
    dx_score VARCHAR(20),
    score_icon VARCHAR(10),
    combo_icon VARCHAR(10),
    sync_icon VARCHAR(10),
    INDEX(user_id)
);
```

#### recent_records テーブル

`best_records` と同じ構造で、最近のプレイ記録を保存します。

### API エンドポイント

#### Webhook 受信

```
POST /linebot/webhook
Headers:
  X-Line-Signature: <signature>
Body: LINE webhook event JSON
```

#### SEGA アカウント連携

```
GET/POST /linebot/sega_bind?token=<token>
```

#### フレンド追加

```
GET /linebot/add_friend?id=<friend_id>
```

#### 管理パネル API

```
GET/POST /linebot/admin                    # 管理者ログイン/ダッシュボード
GET      /linebot/admin/logout             # ログアウト
POST     /linebot/admin/trigger_update     # ユーザー更新トリガー
POST     /linebot/admin/edit_user          # ユーザーデータ編集
POST     /linebot/admin/delete_user        # ユーザー削除
POST     /linebot/admin/get_user_data      # ユーザーデータ取得
POST     /linebot/admin/load_nicknames     # ニックネーム一括読み込み
POST     /linebot/admin/clear_cache        # ニックネームキャッシュクリア
POST     /linebot/admin/cancel_task        # タスクキャンセル
GET      /linebot/admin/task_status        # タスク状態取得
GET      /linebot/admin/get_logs           # ログ取得
GET      /linebot/admin/memory_stats       # メモリ統計取得
POST     /linebot/admin/trigger_cleanup    # 手動メモリクリーンアップ
```

### 設定リファレンス

#### 完全な config.json

```json
{
    "admin_id": ["U0123..."],              // LINE 管理者ユーザー ID
    "admin_password": "secure_pwd",        // 管理パネルパスワード
    "maimai_version": {
        "jp": ["PRiSM PLUS", "CiRCLE"],    // 日本版バージョン
        "intl": ["PRiSM PLUS"]             // 海外版バージョン
    },
    "domain": "jietng.example.com",        // サービスドメイン
    "port": 5100,                          // サービスポート
    "file_path": {
        "dxdata_list": "./data/dxdata.json",
        "dxdata_version": "./data/dxdata_version.json",
        "re_dxdata_list": "./data/re_dxdata.csv",
        "user_list": "./data/user.json.enc",
        "notice_file": "./data/notice.json",
        "font": "./assets/fonts/mplus-jietng.ttf",
        "logo": "./assets/pics/logo.jpg"
    },
    "record_database": {
        "host": "localhost",
        "user": "jietng",
        "password": "your_password",
        "database": "records"
    },
    "urls": {
        "line_adding": "https://line.me/R/ti/p/@yourlineid",
        "support_page": "https://github.com/Matsuk1/JiETNG/blob/main/COMMANDS.md",
        "dxdata": [
            "https://raw.githubusercontent.com/gekichumai/dxrating/refs/heads/main/packages/dxdata/dxdata.json",
            "https://dp4p6x0xfi5o9.cloudfront.net/maimai/data.json"
        ]
    },
    "line_channel": {
        "account_id": "@yourlineid",
        "access_token": "YOUR_TOKEN",
        "secret": "YOUR_SECRET"
    },
    "keys": {
        "user_data": "AUTO_GENERATED_KEY",     // 自動生成 Fernet キー
        "bind_token": "AUTO_GENERATED_TOKEN",  // 自動生成バインドトークン
        "imgur_client_id": "YOUR_IMGUR_CLIENT_ID"  // Imgur API Client ID（オプション）
    }
}
```

---

## トラブルシューティング

### よくある問題

#### SSL 証明書エラー

**問題**: `SSL: CERTIFICATE_VERIFY_FAILED`

**解決方法**:
```bash
pip install --upgrade certifi
```

#### データベース接続失敗

**問題**: `Can't connect to MySQL server`

**確認**:
```bash
# MySQL ステータスを確認
sudo systemctl status mysql

# ユーザー権限を確認
mysql -u jietng -p
SHOW GRANTS FOR 'jietng'@'localhost';
```

#### LINE Webhook 検証失敗

**問題**: `InvalidSignatureError`

**確認**:
- config.json の `line_channel.secret` が正しいか確認
- LINE Developers Console の Webhook URL が正しいか確認
- HTTPS が有効になっているか確認（LINE が要求）

#### 画像生成失敗

**問題**: フォントやアイコンの欠落

**解決方法**:
```bash
# フォントファイルを確認
ls assets/fonts/mplus-jietng.ttf

# アイコンディレクトリを確認
ls assets/icon/combo/
ls assets/icon/score/
```

#### 管理パネルログイン失敗

**問題**: パスワードが間違っているか未設定

**解決方法**:
```json
// config.json に admin_password が存在するか確認
{
    "admin_password": "your_password"
}
```

```bash
# サービスを再起動して設定を反映
sudo systemctl restart jietng
```

### ログ表示

```bash
# リアルタイムログを表示
tail -f jietng.log

# systemd を使用
journalctl -u jietng -f
```

---

## コントリビューション

Issue と Pull Request の提出を歓迎します！

### 開発フロー

1. このリポジトリをフォーク
2. フィーチャーブランチを作成：`git checkout -b feature/your-feature`
3. 変更をコミット：`git commit -am 'Add some feature'`
4. ブランチをプッシュ：`git push origin feature/your-feature`
5. Pull Request を提出

### コード規約

- PEP 8 コーディング規約に従う
- 型アノテーションを追加
- docstring を記述
- 提出前にテストを実行（利用可能な場合）

---

## ライセンス

**Copyright © 2025 Matsuki. All Rights Reserved.**

本ソフトウェアはプロプライエタリソフトウェアです。著作権者の明示的な書面による許可なく、本ソフトウェアの複製、変更、配布、使用は固く禁じられています。

詳細は [LICENSE](LICENSE) をご覧ください。

---

## 謝辞

- [LINE Messaging API](https://developers.line.biz/) - メッセージプラットフォーム
- [Maimai DX](https://maimai.sega.jp/) - SEGA オリジナルゲーム
- [DXRating](https://github.com/gekichumai/dxrating) - 楽曲データソース
- [arcade-songs](https://arcade-songs.zetaraku.dev) - アーケードゲーム楽曲データベース
- すべてのコントリビューターとユーザー

---

## お問い合わせ

- **プロジェクト**: https://github.com/Matsuk1/JiETNG
- **Issue**: https://github.com/Matsuk1/JiETNG/issues
- **LINE Bot**: [@299bylay](https://line.me/R/ti/p/@299bylay)

---

<div align="center">

**このプロジェクトが役に立ったら、ぜひ Star をください！**

製作者: [Matsuk1](https://github.com/Matsuk1)

</div>

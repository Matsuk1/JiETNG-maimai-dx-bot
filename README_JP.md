# JiETNG - LINE Bot

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="100" />

**Maimai DX スコア追跡とデータ管理システム**

日本版と海外版に対応

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.21.0-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

[简体中文](README.md) | [English](README_EN.md) | 日本語

<a href="https://lin.ee/Q6O7aI8"><img src="https://scdn.line-apps.com/n/line_add_friends/btn/ja.png" alt="友だち追加" height="36" border="0"></a>

[機能](#機能) • [コマンドリスト](https://jietng.matsuk1.com/ja/commands/) • [オンラインドキュメント](https://jietng.matsuk1.com/ja/) • [クイックスタート](#クイックスタート) • [管理パネル](#管理パネル) • [デプロイガイド](#デプロイガイド) • [開発ドキュメント](#開発ドキュメント)

</div>

---

## プロジェクト概要

**JiETNG** は、Maimai DX プレイヤー向けの包括的な LINE Bot サービスで、スコア追跡、データ分析、およびさまざまなゲーム補助機能を提供します。日本版（JP）と海外版（INTL）の両方に対応しています。

### コア機能

- **スコア追跡**: Best/Recent ゲーム記録の自動同期と保存
- **データ可視化**: 詳細な B50 スコアチャート生成、カスタムフィルター対応
- **フレンドシステム**: フレンドスコアの閲覧、フレンド申請管理
- **ランキング**: DX Rating ユーザーランキング（日本版・海外版別対応）
- **バージョン進捗**: 各バージョンの達成状況追跡（極/将/神/舞舞）
- **楽曲推薦**: 難易度定数によるランダム楽曲推薦
- **位置情報サービス**: 近くの Maimai 設置店舗を検索
- **管理パネル**: 完全な Web 管理インターフェース
- **パフォーマンス最適化**: デュアルキューアーキテクチャ（画像キュー/ネットワークキュー）と頻度制限
- **多言語対応**: 日本語/英語/中国語インターフェース、多言語ドキュメント

---

## 機能

### 主要機能

- **アカウント管理**: SEGA アカウント連携、表示、連携解除
- **スコア照会**: B50/B40/B35/B15/AB50/AP50/RCT50/IDEALB50 など多種類のスコア図
- **高度なフィルター**: 譜面定数、Rating、達成率、DX スコアなど複数条件の組み合わせフィルター
- **楽曲検索**: 楽曲情報検索、個人スコア照会、ランダム選曲
- **バージョン達成**: 極/将/神/舞舞称号の達成状況追跡
- **フレンド機能**: フレンドリスト、フレンド B50 閲覧
- **ユーティリティ**: Rating 計算、スコア計算機
- **位置情報サービス**: 位置情報送信で近くの Maimai 設置店舗を検索

### 完全コマンドリスト

詳細なコマンド説明と使用例は **[オンラインコマンドドキュメント](https://jietng.matsuk1.com/ja/commands/)** をご覧ください

---

## 管理パネル

Web ベースの管理インターフェースで、包括的なユーザーとシステム管理機能を提供します。

### アクセス URL

```
https://your-domain.com/admin/panel
```

### 機能モジュール

| モジュール | 説明 |
|-----------|------|
| **ユーザー管理** | 全ユーザー表示、ユーザーデータ編集、ユーザー削除、更新トリガー |
| **リアルタイムニックネーム** | LINE SDK から自動取得しキャッシュ（5分間キャッシュ） |
| **デュアルキュー監視** | 画像キュー（3並列）+ ネットワークキュー（1並列） |
| **タスク追跡** | 最近 20 件の完了タスクと実行時間統計を表示 |
| **頻度制限** | 30秒以内の重複リクエストを防止（各タスクタイプ最大2件） |
| **ビジネス分析** | DAU/WAU/MAU、定着率分析、今日の画像生成/同期/連携統計、コマンド分布、30日間DAUトレンドチャート、時間帯別ヒートマップ |
| **システム監視** | CPU/メモリ使用率、キュー状態、スレッド数、稼働時間（折りたたみ可能） |
| **リアルタイムログ** | 最近 100 行のログ表示、ANSI カラーコード対応 |
| **データリフレッシュ** | 個別ユーザーデータとニックネームの高速リフレッシュ |

### 主な特徴

- **遅延読み込み**: ログイン後すぐにページ表示、ニックネームは非同期読み込み
- **レスポンシブデザイン**: デスクトップとモバイルデバイスに完全対応
- **デュアルキューアーキテクチャ**: 画像生成とネットワークタスクを分離し、並列性能を向上
- **タスク追跡**: 実行中/待機中/完了タスクと所要時間統計をリアルタイム表示
- **ビジネス分析**: MySQL events テーブルベースのイベント追跡、DAU/WAU/MAU 自動集計、30日間トレンドチャート、時間帯別分布ヒートマップ
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

1. `https://your-domain.com/admin/panel` にアクセス
2. 管理者パスワードでログイン
3. 6つの主要タブでナビゲーション：
   - **Users**: ユーザーリストとデータ管理
   - **Task Queue**: デュアルキュー監視（画像 + ネットワークキュー）
   - **Statistics**: ビジネス分析（DAU/WAU/MAU、今日のアクティビティ、トレンドチャート）+ システムヘルス監視
   - **Notices**: お知らせ管理
   - **DXData**: 楽曲データベース管理と更新
   - **Logs**: リアルタイムログビューア

---

## クイックスタート

### システム要件

- **Python**: 3.10 以上
- **MySQL**: 5.7+ / MariaDB 10.2+
- **OS**: Linux / macOS / Windows

### インストール手順

#### 1. リポジトリをクローン

```bash
git clone https://github.com/Matsuk1/JiETNG.git
cd JiETNG
```

#### 2. Python 依存関係をインストール

```bash
pip install -r requirements.txt
```

#### 3. データベースを設定

```bash
# MySQL にログイン
mysql -u root -p

# データベースとユーザーを作成
CREATE DATABASE maimai_records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jietng'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON maimai_records.* TO 'jietng'@'localhost';
FLUSH PRIVILEGES;

# データベース構造をインポート
mysql -u jietng -p maimai_records < records_db.sql
```

#### 4. LINE Channel 認証情報を取得

1. [LINE Developers Console](https://developers.line.biz/) にアクセス
2. Messaging API Channel を作成
3. **Channel Access Token** と **Channel Secret** を取得
4. Webhook URL を設定：`https://your-domain.com/linebot/webhook`
5. **Use webhook** を有効化

#### 5. config.json を設定

`config.json` ファイルを編集（完全な構造は[設定リファレンス](#完全な-configjson)を参照）：

```json
{
    "admin_password": "your_admin_password",
    "domain": "your-domain.com",
    "host": "0.0.0.0",
    "port": 5000,
    "line_channel": {
        "account_id": "@yourlineid",
        "access_token": "YOUR_CHANNEL_ACCESS_TOKEN",
        "secret": "YOUR_CHANNEL_SECRET"
    },
    "record_database": {
        "host": "localhost",
        "user": "jietng",
        "password": "your_password",
        "database": "maimai_records"
    },
    "urls": {
        "line_adding": "https://line.me/R/ti/p/@yourlineid",
        "support_page": "https://your-domain.com/commands/",
        "dxdata": [
            "https://raw.githubusercontent.com/gekichumai/dxrating/refs/heads/main/packages/dxdata/dxdata.json",
            "https://dp4p6x0xfi5o9.cloudfront.net/maimai/data.json"
        ]
    },
    "keys": {
        "bind_token": ""
    }
}
```

#### 6. サービスを起動

```bash
python main.py
```

サービスは `http://0.0.0.0:<port>` で起動します（ポートは config.json の `port` で設定）

### 本番環境デプロイ（推奨）

```bash
gunicorn -w 1 --threads 8 -b 0.0.0.0:5000 --timeout 120 main:app
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
EXPOSE 5000

# 起動コマンド
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "--timeout", "120", "main:app"]
```

#### docker-compose.yml を作成

```yaml
version: '3.8'

services:
  jietng:
    build: .
    container_name: jietng_bot
    ports:
      - "5000:5000"
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
        proxy_pass http://127.0.0.1:5000;
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
├── requirements.txt           # Python 依存関係
├── records_db.sql             # データベーススキーマ
├── modules/                   # 機能モジュール
│   ├── api/                   # Flask API Blueprint と開発者認証
│   ├── backup_manager.py      # バックアップ管理
│   ├── bindtoken_manager.py   # バインドトークン管理
│   ├── commands/              # コマンドルーティング、解析、ヘルプ、設定
│   ├── config_loader.py       # 設定ローダー
│   ├── dbpool_manager.py      # データベース接続プール
│   ├── devtoken_manager.py    # 開発者トークン管理
│   ├── dxdata_manager.py      # 楽曲データ管理
│   ├── event_tracker.py       # ビジネスイベント追跡と指標集計
│   ├── image_cache.py         # 画像キャッシュ
│   ├── image_manager.py       # 画像処理
│   ├── image_uploader.py      # 画像アップロード（Imgur/Cloudflare R2）
│   ├── json_encrypt.py        # 暗号化ツール
│   ├── line_messenger.py      # LINE メッセージ送信
│   ├── maimai_manager.py      # Maimai API インターフェース
│   ├── memory_manager.py      # メモリ管理とクリーンアップ
│   ├── message_manager.py     # 多言語メッセージ管理
│   ├── message_texts.py       # 多言語メッセージテキスト定義
│   ├── notice_manager.py      # お知らせシステム
│   ├── notice_stats.py        # お知らせ統計
│   ├── notification_manager.py # システム通知管理（Web Push）
│   ├── perm_request_generator.py  # 権限リクエスト生成器
│   ├── perm_request_handler.py    # 権限リクエストハンドラー
│   ├── rate_limiter.py        # 頻度制限 + リクエスト追跡
│   ├── record_generator.py    # スコアチャート生成
│   ├── record_manager.py      # データベース操作
│   ├── score_recognition/     # スコア OCR ランタイムパイプラインとモデル
│   ├── song_generator.py      # 楽曲チャート生成
│   ├── song_matcher.py        # 楽曲検索（あいまい一致対応）
│   ├── storelist_generator.py # 設置店舗リスト生成（Flex Message）
│   ├── system_checker.py      # システム自己診断
│   ├── tip_ad_manager.py      # 更新後ヒント/広告管理
│   └── user_manager.py        # ユーザー管理 + ニックネームキャッシュ
├── templates/                 # HTML テンプレート
│   ├── admin_login.html       # 管理者ログインページ
│   ├── admin_panel.html       # 管理パネルインターフェース
│   ├── bind_form.html         # アカウント連携フォーム
│   ├── common_styles.html     # 共通スタイル
│   ├── error.html             # エラーページ
│   ├── loading.html           # ローディング遷移ページ
│   └── success.html           # 成功ページ
├── data/                      # データファイル
│   ├── dxdata/                # 楽曲データベースディレクトリ
│   │   ├── dxdata.json        # 楽曲定数データ
│   │   ├── dxdata_version.json # バージョン情報
│   │   └── intl_override.csv  # 海外版オーバーライドデータ
│   ├── images/                # 生成画像キャッシュ
│   ├── backup/                # データバックアップ
│   ├── notice.json            # お知らせ情報
│   ├── tip_ad.json            # 更新後ヒント/広告設定
│   └── user.json.enc          # ユーザーデータ（暗号化）
└── assets/                    # 静的リソース
    ├── fonts/                 # フォントファイル
    ├── pics/                  # 画像（ロゴ等）
    ├── covers/                # 楽曲カバー画像
    ├── plates/                # 称号プレート画像
    ├── versions/              # バージョンアイコン
    └── icon/                  # アイコンリソース
        ├── combo/             # Full Combo アイコン
        ├── combo_rcd/         # レコードページ Combo アイコン
        ├── dx_star/           # DX Star アイコン
        ├── score/             # スコアランクアイコン
        ├── sync/              # Full Sync アイコン
        ├── sync_rcd/          # レコードページ Sync アイコン
        └── type/              # 譜面タイプアイコン（DX/STD）
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

#### events テーブル

```sql
CREATE TABLE events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NULL,
    event_type VARCHAR(32) NOT NULL,
    metadata JSON NULL,
    ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ts (ts),
    INDEX idx_event_ts (event_type, ts),
    INDEX idx_user_ts (user_id, ts)
);
```

ビジネスイベント追跡テーブル。起動時に自動作成されます。Webhook 呼び出し、画像生成、連携/解除、同期タスクなどのイベントを記録し、DAU/WAU/MAU などの指標集計を支えます。90日を超える履歴レコードはバックグラウンドスレッドにより自動的にパージされます。

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
GET/POST /admin/panel              # 管理者ログイン/ダッシュボード
GET      /admin/logout             # ログアウト
POST     /admin/trigger_update     # ユーザー更新トリガー
POST     /admin/edit_user          # ユーザーデータ編集
POST     /admin/delete_user        # ユーザー削除
POST     /admin/get_user_data      # ユーザーデータ取得
POST     /admin/load_nicknames     # ニックネーム一括読み込み
POST     /admin/clear_cache        # ニックネームキャッシュクリア
POST     /admin/cancel_task        # タスクキャンセル
GET      /admin/task_status        # タスク状態取得
GET      /admin/get_logs           # ログ取得
```

### 設定リファレンス

#### 完全な config.json

```json
{
    "admin_password": "secure_pwd",        // 管理パネルパスワード
    "maimai_version": {
        "jp": ["PRiSM PLUS", "CiRCLE"],    // 日本版 現行/前バージョン
        "intl": ["PRiSM PLUS"]             // 海外版バージョン
    },
    "temp_version": {
        "abbr": "CiRCLE",                  // 次期バージョン略称
        "title": "CiRCLE"                  // 次期バージョン正式名称
    },
    "domain": "your-domain.com",           // サービスドメイン（プロトコルなし）
    "host": "0.0.0.0",                     // リッスンアドレス
    "port": 5000,                          // サービスポート
    "file_path": {
        "dxdata_list": "./data/dxdata/dxdata.json",
        "dxdata_version": "./data/dxdata/dxdata_version.json",
        "override_list": "./data/dxdata/intl_override.csv",
        "user_list": "./data/user.json.enc",
        "notice_file": "./data/notice.json",
        "tip_ad_file": "./data/tip_ad.json",
        "img_dir": "./data/images",
        "backup": "./data/backup",
        "font": "./assets/fonts/line_seed_jietng.ttf",
        "logo": "./assets/pics/logo.png",
        "covers": "./assets/covers",
        "icon_type": "./assets/icon/type",
        "icon_score": "./assets/icon/score",
        "icon_dx_star": "./assets/icon/dx_star",
        "icon_combo": "./assets/icon/combo",
        "icon_sync": "./assets/icon/sync",
        "icon_base": "./assets/icon",
        "versions": "./assets/versions",
        "plates": "./assets/plates",
        "icon_combo_rcd": "./assets/icon/combo_rcd",
        "icon_sync_rcd": "./assets/icon/sync_rcd"
    },
    "record_database": {
        "host": "localhost",
        "user": "jietng",
        "password": "your_password",
        "database": "maimai_records"
    },
    "urls": {
        "line_adding": "https://line.me/R/ti/p/@yourlineid",
        "support_page": "https://your-domain.com/commands/",
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
        "bind_token": "AUTO_GENERATED_TOKEN"  // 自動生成バインドトークン
    },
    "cloudflare_r2": {
        "enabled": false,                      // Cloudflare R2 画像ストレージを使用するか
        "account_id": "",
        "access_key_id": "",
        "secret_access_key": "",
        "bucket_name": "",
        "public_url": ""
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
ls assets/fonts/line_seed_jietng.ttf

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

**Copyright © 2025 - 2026 Matsuki. All Rights Reserved.**

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

# JiETNG - Maimai DX LINE Bot

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="100" />

**Maimai DX スコア追跡とデータ管理システム**

日本版と国際版に対応

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.14.5-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[简体中文](README.md) | [English](README_EN.md) | 日本語

[機能](#機能) • [コマンドリスト](COMMANDS_JP.md) • [クイックスタート](#クイックスタート) • [管理パネル](#管理パネル) • [デプロイガイド](#デプロイガイド) • [開発ドキュメント](#開発ドキュメント)

</div>

---

## プロジェクト概要

**JiETNG** は、Maimai DX プレイヤー向けの包括的な LINE Bot サービスで、スコア追跡、データ分析、およびさまざまなゲーム補助機能を提供します。日本版（JP）と国際版（INTL）の両方に対応しています。

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
- **多言語対応**: 日本語インターフェース、中英文ドキュメント

---

## 機能

### 主要機能

- **アカウント管理**: SEGA アカウント連携、表示、連携解除
- **スコア照会**: B50/B100/B35/B15/AB50/AP50/RCT50/IDEALB50 など多種類のスコア図
- **高度なフィルター**: 譜面定数、Rating、達成率、DX スコアなど複数条件の組み合わせフィルター
- **楽曲検索**: 楽曲情報検索、個人スコア照会、ランダム選曲
- **バージョン達成**: 極/将/神/舞舞称号の達成状況追跡
- **フレンド機能**: フレンドリスト管理、フレンド B50 閲覧、フレンド追加
- **ユーティリティ**: Rating 計算、スコア計算機、Yang Rating、カード生成
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
│   ├── user_manager.py        # ユーザー管理 + ニックネームキャッシュ
│   ├── maimai_manager.py      # Maimai API インターフェース
│   ├── record_manager.py      # データベース操作
│   ├── record_generator.py    # スコアチャート生成
│   ├── song_generator.py      # 楽曲チャート生成
│   ├── image_manager.py       # 画像処理
│   ├── image_cache.py         # 画像キャッシュ
│   ├── image_uploader.py      # 画像アップロード
│   ├── token_manager.py       # トークン管理
│   ├── friend_list.py         # フレンドインターフェース
│   ├── notice_manager.py      # お知らせシステム
│   ├── dxdata_manager.py      # 楽曲データ管理
│   ├── note_score.py          # スコア計算
│   ├── json_encrypt.py        # 暗号化ツール
│   ├── rate_limiter.py        # 頻度制限 + リクエスト追跡
│   ├── line_messenger.py      # LINE メッセージ送信
│   ├── song_matcher.py        # 楽曲検索（あいまい一致対応）
│   ├── memory_manager.py      # メモリ管理とクリーンアップ
│   ├── system_checker.py      # システム自己診断
│   ├── store_list.py          # 設置店舗リスト生成（Flex Message）
│   ├── friend_request.py      # フレンド申請生成
│   ├── friend_request_handler.py  # フレンド申請処理
│   └── reply_text.py          # メッセージテンプレート（寄付情報と Tips 含む）
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

---

## コントリビューション

Issue と Pull Request の提出を歓迎します！

### 開発フロー

1. このリポジトリをフォーク
2. フィーチャーブランチを作成：`git checkout -b feature/your-feature`
3. 変更をコミット：`git commit -am 'Add some feature'`
4. ブランチをプッシュ：`git push origin feature/your-feature`
5. Pull Request を提出

---

## ライセンス

このプロジェクトは [MIT License](LICENSE) の下でライセンスされています。

---

## 謝辞

- [LINE Messaging API](https://developers.line.biz/) - メッセージプラットフォーム
- [Maimai DX](https://maimai.sega.jp/) - SEGA オリジナルゲーム
- [DXRating](https://github.com/gekichumai/dxrating) - 楽曲データソース
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

# JiETNG - Maimai DX LINE Bot

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="100" />

**Maimai DX Score Tracking and Data Management System for LINE Platform**

Supports Japanese and International servers

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.14.5-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

English | [简体中文](README_ZH.md)

[Features](#features) • [Quick Start](#quick-start) • [Admin Panel](#admin-panel) • [Deployment](#deployment) • [Documentation](#documentation)

</div>

---

## Overview

**JiETNG** is a comprehensive LINE Bot service for Maimai DX players, providing score tracking, data analysis, and various gameplay utilities. It supports both Japanese (JP) and International (INTL) server versions.

### Key Features

- **Score Tracking**: Automatic synchronization and storage of Best/Recent game records
- **Data Visualization**: Generate detailed B50/B100 score charts with customizable filters
- **Friend System**: View friend scores and manage friend requests
- **Version Progress**: Track completion status for version-specific achievements
- **Song Recommendations**: Random song selection by difficulty rating
- **Location Services**: Find nearby Maimai arcade locations
- **Data Security**: SEGA account information encrypted using Fernet encryption
- **Admin Dashboard**: Comprehensive web-based management interface
- **Performance Optimization**: Dual-queue architecture (image/network queues) with rate limiting
- **Multi-language Support**: Japanese interface with English documentation

---

## Features

### Account Management

| Feature | Command | Description |
|---------|---------|-------------|
| Bind Account | `segaid bind` | Link SEGA account to LINE profile |
| View Binding | `getme` | Display current account binding status |
| Unbind Account | `unbind` | Remove account binding |

### Score Queries

#### Score Chart Types

| Command | Description |
|---------|-------------|
| `b50` / `best 50` | Standard B50 (35 old charts + 15 new charts) |
| `b100` / `best 100` | B100 (70 old charts + 30 new charts) |
| `b35` / `b15` | View old/new charts separately |
| `ab50` / `all best 50` | Combined B50 without chart type separation |
| `apb50` | B50 for AP/APP scores only |
| `idealb50` | B50 with ideal theoretical scores |
| `rct50` / `r50` | Recent 50 play records |

#### Advanced Filters

Multiple filter conditions can be combined:

```
b50 -lv 14.0 14.9    # Filter by difficulty rating 14.0-14.9
b50 -ra 200 250      # Filter by rating value 200-250
b50 -scr 99.5        # Filter by achievement rate >= 99.5%
b50 -dx 95           # Filter by DX score percentage >= 95%
```

### Song Queries

| Command Format | Example | Description |
|---------------|---------|-------------|
| `[曲名]ってどんな曲` | `オンゲキってどんな曲` | Search for song information |
| `[曲名]のレコード` | `オンゲキのレコード` | View personal score for a song |
| `ランダム曲 [定数]` | `ランダム曲 14+` | Random song recommendation |
| `[定数]のレコードリスト` | `14+のレコードリスト` | View score list by difficulty |

### Version Progress

| Command | Description |
|---------|-------------|
| `[版本]極の達成状況` | View "Extreme" achievement progress |
| `[版本]将の達成状況` | View "Master" achievement progress |
| `[版本]神の達成状況` | View "God" achievement progress |
| `[版本]舞舞の達成状況` | View "MaiMai" achievement progress |

Version abbreviations: `真`, `超`, `晓`, `祭`, `煌`, `镜`, etc.

### Friend Features

| Command | Description |
|---------|-------------|
| `friend list` | Display friend list |
| `friend-b50 [friend_code]` | View friend's B50 chart |
| `add-friend [friend_code]` | Send friend request |
| `maid card` / `maid` | Generate profile card with QR code |

### Utility Functions

| Command | Description |
|---------|-------------|
| `maimai update` | Update score data from server |
| `rc [rating]` | View rating reference table |
| `calc [tap] [hold] [slide] [touch] [break]` | Calculate theoretical score |
| `yang` / `yra` | View Yang Rating |
| `[版本]のバージョンリスト` | View version song list |

### Location Services

Send location information to the bot to automatically find nearby Maimai arcade locations with map links.

---

## Admin Panel

Web-based administration interface providing comprehensive user and system management.

### Access

```
https://your-domain.com/linebot/admin
```

### Features

| Module | Description |
|--------|-------------|
| **User Management** | View all users, edit user data, delete users, trigger updates |
| **Real-time Nicknames** | Automatic nickname caching from LINE SDK (5-minute cache) |
| **Dual Queue Monitoring** | Image queue (3 concurrent) + Network queue (1 concurrent) |
| **Task Tracking** | Display recent 20 completed tasks with execution time statistics |
| **Rate Limiting** | Prevent duplicate requests within 30-second window (max 2 per task type) |
| **System Statistics** | User count, version distribution, CPU/memory usage, queue status, uptime |
| **Real-time Logs** | View recent 100 log lines with ANSI color code support |
| **Data Refresh** | Quick refresh for individual user data and nicknames |

### Key Highlights

- **Lazy Loading**: Immediate page display after login with asynchronous nickname loading
- **Responsive Design**: Full support for desktop and mobile devices
- **Dual Queue Architecture**: Separate image generation and network tasks for improved concurrency
- **Task Tracking**: Real-time display of running/queued/completed tasks with timing statistics
- **Smart Rate Limiting**: Protect server resources from rapid repeated requests
- **Colored Logs**: ANSI color code support for easy error/warning identification
- **Session Management**: Cookie-based secure authentication
- **State Persistence**: Maintain current tab after page refresh

### Configuration

Add admin password in `config.json`:

```json
{
    "admin_password": "your_secure_password"
}
```

### Usage

1. Access `https://your-domain.com/linebot/admin`
2. Login with admin password
3. Navigate through five main tabs:
   - **Users**: User list and data management
   - **Task Queue**: Dual queue monitoring (image + network queues)
   - **Statistics**: System statistics and information
   - **Notices**: Announcement management
   - **Logs**: Real-time log viewer

---

## Quick Start

### System Requirements

- **Python**: 3.8 or higher
- **MySQL**: 5.7+ / MariaDB 10.2+
- **Operating System**: Linux / macOS / Windows

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/Matsuk1/JiETNG.git
cd JiETNG
```

#### 2. Install Dependencies

```bash
pip install -r inits/requirements.txt
```

#### 3. Configure Database

```bash
# Login to MySQL
mysql -u root -p

# Create database and user
CREATE DATABASE records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jietng'@'localhost' IDENTIFIED BY 'jietng_2025';
GRANT ALL PRIVILEGES ON records.* TO 'jietng'@'localhost';
FLUSH PRIVILEGES;

# Import database structure
mysql -u jietng -p records < inits/records_db.sql
```

#### 4. Configure config.json

Edit `config.json` with your settings:

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

#### 5. Obtain LINE Channel Credentials

1. Visit [LINE Developers Console](https://developers.line.biz/)
2. Create a Messaging API Channel
3. Obtain **Channel Access Token** and **Channel Secret**
4. Set Webhook URL: `https://your-domain.com/linebot/webhook`
5. Enable **Use webhook**

#### 6. Start Service

```bash
python main.py
```

Service will start on `http://0.0.0.0:5100`

### Production Deployment (Recommended)

```bash
gunicorn -w 4 -b 0.0.0.0:5100 --timeout 120 main:app
```

---

## Deployment

### Using Docker (Recommended)

#### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY inits/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 5100

# Start command
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5100", "--timeout", "120", "main:app"]
```

#### Create docker-compose.yml

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
      - ./inits/records_db.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

volumes:
  mysql_data:
```

#### Start Containers

```bash
docker-compose up -d
```

### Using Systemd (Linux)

Create `/etc/systemd/system/jietng.service`:

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

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable jietng
sudo systemctl start jietng
```

### Using Nginx Reverse Proxy

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

        # LINE Webhook settings
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

Enable HTTPS (recommended):

```bash
sudo certbot --nginx -d your-domain.com
```

---

## Documentation

### Project Structure

```
JiETNG/
├── main.py                    # Flask application entry point
├── config.json                # Configuration file
├── README.md                  # This document
├── inits/                     # Initialization files
│   ├── requirements.txt       # Python dependencies
│   └── records_db.sql         # Database schema
├── modules/                   # Functional modules
│   ├── config_loader.py       # Configuration loader
│   ├── db_pool.py             # Database connection pool
│   ├── user_console.py        # User management + nickname cache
│   ├── maimai_console.py      # Maimai API interface
│   ├── record_console.py      # Database operations
│   ├── record_generate.py     # Score chart generation
│   ├── song_generate.py       # Song chart generation
│   ├── img_console.py         # Image processing
│   ├── img_cache.py           # Image caching
│   ├── img_upload.py          # Image hosting upload
│   ├── token_console.py       # Token management
│   ├── friend_list.py         # Friend interface
│   ├── notice_console.py      # Notification system
│   ├── dxdata_console.py      # Song data management
│   ├── note_score.py          # Score calculation
│   ├── json_encrypt.py        # Encryption utilities
│   ├── rate_limiter.py        # Rate limiting + request tracking
│   ├── line_messenger.py      # LINE message sending
│   ├── song_matcher.py        # Song search with fuzzy matching
│   ├── memory_manager.py      # Memory management and cleanup
│   ├── system_check.py        # System self-check
│   └── reply_text.py          # Message templates
├── templates/                 # HTML templates
│   ├── bind_form.html         # Account binding form
│   ├── success.html           # Success page
│   ├── error.html             # Error page
│   ├── admin_login.html       # Admin login page
│   ├── admin_panel.html       # Admin dashboard
│   └── stats.html             # Statistics page
├── data/                      # Data files
│   ├── dxdata.json            # Song database
│   ├── notice.json            # Announcements
│   ├── re_dxdata.csv          # Regional data
│   └── user.json.enc          # User data (encrypted)
└── assets/                    # Static resources
    ├── fonts/                 # Font files
    ├── pics/                  # Images
    └── icon/                  # Icon resources
```

### Database Schema

#### best_records Table

```sql
CREATE TABLE best_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    difficulty VARCHAR(50),
    kind VARCHAR(50),
    score VARCHAR(50),
    dx_score VARCHAR(50),
    score_icon VARCHAR(50),
    combo_icon VARCHAR(50),
    sync_icon VARCHAR(50),
    INDEX idx_user_id (user_id)
);
```

#### recent_records Table

Same structure as `best_records`, stores recent play records.

### API Endpoints

#### Webhook Reception

```
POST /linebot/webhook
Headers:
  X-Line-Signature: <signature>
Body: LINE webhook event JSON
```

#### SEGA Account Binding

```
GET/POST /linebot/sega_bind?token=<token>
```

#### Friend Addition

```
GET /linebot/add_friend?code=<friend_code>
```

#### Admin Dashboard API

```
GET/POST /linebot/admin                    # Admin login/dashboard
GET      /linebot/admin/logout             # Logout
POST     /linebot/admin/trigger_update     # Trigger user update
POST     /linebot/admin/edit_user          # Edit user data
POST     /linebot/admin/delete_user        # Delete user
POST     /linebot/admin/get_user_data      # Get user data
POST     /linebot/admin/load_nicknames     # Batch load nicknames
POST     /linebot/admin/clear_cache        # Clear nickname cache
POST     /linebot/admin/cancel_task        # Cancel task
GET      /linebot/admin/task_status        # Get task status
GET      /linebot/admin/get_logs           # Get logs
GET      /linebot/admin/memory_stats       # Get memory stats
POST     /linebot/admin/trigger_cleanup    # Manual memory cleanup
```

### Configuration Reference

#### Complete config.json

```json
{
    "admin_id": ["U0123..."],              // LINE admin user IDs
    "admin_password": "secure_pwd",        // Admin panel password
    "maimai_version": {
        "jp": ["PRiSM PLUS", "CiRCLE"],    // JP server versions
        "intl": ["PRiSM PLUS"]             // International versions
    },
    "domain": "jietng.example.com",        // Service domain
    "port": 5100,                          // Service port
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
        "user_data": "AUTO_GENERATED_KEY",     // Auto-generated Fernet key
        "bind_token": "AUTO_GENERATED_TOKEN"   // Auto-generated bind token
    }
}
```

---

## Troubleshooting

### Common Issues

#### SSL Certificate Error

**Problem**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution**:
```bash
pip install --upgrade certifi
```

#### Database Connection Failed

**Problem**: `Can't connect to MySQL server`

**Check**:
```bash
# Check MySQL status
sudo systemctl status mysql

# Check user permissions
mysql -u jietng -p
SHOW GRANTS FOR 'jietng'@'localhost';
```

#### LINE Webhook Verification Failed

**Problem**: `InvalidSignatureError`

**Check**:
- Verify `line_channel.secret` in config.json is correct
- Confirm Webhook URL in LINE Developers Console
- Ensure HTTPS is enabled (required by LINE)

#### Image Generation Failed

**Problem**: Missing fonts or icons

**Solution**:
```bash
# Verify font file exists
ls assets/fonts/mplus-jietng.ttf

# Verify icon directories
ls assets/icon/combo/
ls assets/icon/score/
```

#### Admin Panel Login Failed

**Problem**: Password incorrect or not configured

**Solution**:
```json
// Confirm admin_password exists in config.json
{
    "admin_password": "your_password"
}
```

```bash
# Restart service to apply configuration
sudo systemctl restart jietng
```

### Log Viewing

```bash
# View real-time logs
tail -f jietng.log

# Using systemd
journalctl -u jietng -f
```

---

## Contributing

Contributions are welcome! Please submit Issues and Pull Requests.

### Development Workflow

1. Fork this repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add some feature'`
4. Push branch: `git push origin feature/your-feature`
5. Submit Pull Request

### Code Standards

- Follow PEP 8 coding standards
- Add type annotations
- Write docstrings
- Run tests before submission (if available)

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

- [LINE Messaging API](https://developers.line.biz/) - Messaging platform
- [Maimai DX](https://maimai.sega.jp/) - Original game by SEGA
- [DXRating](https://github.com/gekichumai/dxrating) - Song data source
- All contributors and users

---

## Contact

- **Repository**: https://github.com/Matsuk1/JiETNG
- **Issues**: https://github.com/Matsuk1/JiETNG/issues
- **LINE Bot**: [@299bylay](https://line.me/R/ti/p/@299bylay)

---

<div align="center">

**If you find this project helpful, please give it a star!**

Made by [Matsuk1](https://github.com/Matsuk1)

</div>

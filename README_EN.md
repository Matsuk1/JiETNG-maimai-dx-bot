# JiETNG - LINE Bot

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="100" />

**Maimai DX Score Tracking and Data Management System for LINE Platform**

Supports Japanese and International servers

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.21.0-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

[简体中文](README.md) | English | [日本語](README_JP.md)

<a href="https://lin.ee/Q6O7aI8"><img src="https://scdn.line-apps.com/n/line_add_friends/btn/ja.png" alt="Add Friend" height="36" border="0"></a>

[Features](#features) • [Command List](https://jietng.matsuk1.com/en/commands/) • [Online Docs](https://jietng.matsuk1.com/en/) • [Quick Start](#quick-start) • [Admin Panel](#admin-panel) • [Deployment](#deployment) • [Documentation](#documentation)

</div>

---

## Overview

**JiETNG** is a comprehensive LINE Bot service for Maimai DX players, providing score tracking, data analysis, and various gameplay utilities. It supports both Japanese (JP) and International (INTL) server versions.

### Key Features

- **Score Tracking**: Automatic synchronization and storage of Best/Recent game records
- **Data Visualization**: Generate detailed B50 score charts with customizable filters
- **Friend System**: View friend scores and manage friend requests
- **Leaderboard**: DX Rating user rankings with separate JP/INTL server views
- **Version Progress**: Track completion status for version-specific achievements
- **Song Recommendations**: Random song selection by difficulty rating
- **Location Services**: Find nearby Maimai arcade locations
- **Admin Dashboard**: Comprehensive web-based management interface
- **Performance Optimization**: Dual-queue architecture (image/network queues) with rate limiting
- **Multi-language Support**: Japanese/English/Chinese interface with multilingual documentation

### Complete Command List

Detailed commands list is here **[Online Command Docs](https://jietng.matsuk1.com/en/commands/)**

---

## Admin Panel

Web-based administration interface providing comprehensive user and system management.

### Access

```
https://your-domain.com/admin/panel
```

### Features

| Module | Description |
|--------|-------------|
| **User Management** | View all users, edit user data, delete users, trigger updates |
| **Real-time Nicknames** | Automatic nickname caching from LINE SDK (5-minute cache) |
| **Dual Queue Monitoring** | Image queue (3 concurrent) + Network queue (1 concurrent) |
| **Task Tracking** | Display recent 20 completed tasks with execution time statistics |
| **Rate Limiting** | Prevent duplicate requests within 30-second window (max 2 per task type) |
| **Business Analytics** | DAU/WAU/MAU, stickiness analysis, today's image/sync/bind stats, command breakdown, 30-day DAU trend chart, hourly heatmap |
| **System Monitoring** | CPU/memory usage, queue status, thread count, uptime (collapsible) |
| **Real-time Logs** | View recent 100 log lines with ANSI color code support |
| **Data Refresh** | Quick refresh for individual user data and nicknames |

### Key Highlights

- **Lazy Loading**: Immediate page display after login with asynchronous nickname loading
- **Responsive Design**: Full support for desktop and mobile devices
- **Dual Queue Architecture**: Separate image generation and network tasks for improved concurrency
- **Task Tracking**: Real-time display of running/queued/completed tasks with timing statistics
- **Business Analytics**: MySQL events-based event tracking with automatic DAU/WAU/MAU aggregation, 30-day trend charts, and hourly distribution heatmaps
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

1. Access `https://your-domain.com/admin/panel`
2. Login with admin password
3. Navigate through five main tabs:
   - **Users**: User list and data management
   - **Task Queue**: Dual queue monitoring (image + network queues)
   - **Statistics**: Business analytics (DAU/WAU/MAU, today's activity, trend charts) + system health monitoring
   - **Notices**: Announcement management
   - **DXData**: Song database management and updates
   - **Logs**: Real-time log viewer

---

## Quick Start

### System Requirements

- **Python**: 3.10 or higher
- **MySQL**: 5.7+ / MariaDB 10.2+
- **Operating System**: Linux / macOS / Windows

### Installation

#### 1. Clone Repository

```bash
git clone https://github.com/Matsuk1/JiETNG.git
cd JiETNG
```

#### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Database

```bash
# Login to MySQL
mysql -u root -p

# Create database and user
CREATE DATABASE maimai_records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jietng'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON maimai_records.* TO 'jietng'@'localhost';
FLUSH PRIVILEGES;

# Import database structure
mysql -u jietng -p maimai_records < records_db.sql
```

#### 4. Obtain LINE Channel Credentials

1. Visit [LINE Developers Console](https://developers.line.biz/)
2. Create a Messaging API Channel
3. Obtain **Channel Access Token** and **Channel Secret**
4. Set Webhook URL: `https://your-domain.com/linebot/webhook`
5. Enable **Use webhook**

#### 5. Configure config.json

Edit `config.json` (see [Configuration Reference](#complete-configjson) for full structure):

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

#### 6. Start Service

```bash
python main.py
```

Service will start on `http://0.0.0.0:<port>` (port configured in config.json)

### Production Deployment (Recommended)

```bash
gunicorn -w 1 --threads 8 -b 0.0.0.0:5000 --timeout 120 main:app
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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 5000

# Start command
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "--timeout", "120", "main:app"]
```

#### Create docker-compose.yml

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
        proxy_pass http://127.0.0.1:5000;
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
├── README.md                  # Chinese documentation
├── README_EN.md               # English documentation (this file)
├── README_JP.md               # Japanese documentation
├── requirements.txt           # Python dependencies
├── records_db.sql             # Database schema
├── modules/                   # Functional modules
│   ├── api/                   # Flask API blueprints and developer auth
│   ├── backup_manager.py      # Backup management
│   ├── bindtoken_manager.py   # Bind token management
│   ├── commands/              # Command routing, parsing, help, and config
│   ├── config_loader.py       # Configuration loader
│   ├── dbpool_manager.py      # Database connection pool
│   ├── devtoken_manager.py    # Developer token management
│   ├── dxdata_manager.py      # Song data management
│   ├── event_tracker.py       # Business event tracking and metrics aggregation
│   ├── image_cache.py         # Image caching
│   ├── image_manager.py       # Image processing
│   ├── image_uploader.py      # Image upload (Imgur/Cloudflare R2)
│   ├── json_encrypt.py        # Encryption utilities
│   ├── line_messenger.py      # LINE message sending
│   ├── maimai_manager.py      # Maimai API interface
│   ├── memory_manager.py      # Memory management and cleanup
│   ├── message_manager.py     # Multi-language message management
│   ├── message_texts.py       # Multi-language message text definitions
│   ├── notice_manager.py      # Announcement system
│   ├── notice_stats.py        # Announcement statistics
│   ├── notification_manager.py # System notification management (Web Push)
│   ├── perm_request_generator.py  # Permission request generator
│   ├── perm_request_handler.py    # Permission request handler
│   ├── rate_limiter.py        # Rate limiting + request tracking
│   ├── record_generator.py    # Score chart generation
│   ├── record_manager.py      # Database operations
│   ├── score_recognition/     # Score OCR runtime pipeline and models
│   ├── song_generator.py      # Song chart generation
│   ├── song_matcher.py        # Song search with fuzzy matching
│   ├── storelist_generator.py # Arcade store list generation (Flex Message)
│   ├── system_checker.py      # System self-check
│   ├── tip_ad_manager.py      # Post-update tip/ad management
│   └── user_manager.py        # User management + nickname cache
├── templates/                 # HTML templates
│   ├── admin_login.html       # Admin login page
│   ├── admin_panel.html       # Admin dashboard
│   ├── bind_form.html         # Account binding form
│   ├── common_styles.html     # Common styles
│   ├── error.html             # Error page
│   ├── loading.html           # Loading transition page
│   └── success.html           # Success page
├── data/                      # Data files
│   ├── dxdata/                # Song database directory
│   │   ├── dxdata.json        # Song constant data
│   │   ├── dxdata_version.json # Version information
│   │   └── intl_override.csv  # International server overrides
│   ├── images/                # Generated image cache
│   ├── backup/                # Data backups
│   ├── notice.json            # Announcements
│   ├── tip_ad.json            # Post-update tip/ad config
│   └── user.json.enc          # User data (encrypted)
└── assets/                    # Static resources
    ├── fonts/                 # Font files
    ├── pics/                  # Images (logo, etc.)
    ├── covers/                # Song cover images
    ├── plates/                # Nameplate images
    ├── versions/              # Version icons
    └── icon/                  # Icon resources
        ├── combo/             # Full Combo icons
        ├── combo_rcd/         # Record page Combo icons
        ├── dx_star/           # DX Star icons
        ├── score/             # Score rank icons
        ├── sync/              # Full Sync icons
        ├── sync_rcd/          # Record page Sync icons
        └── type/              # Chart type icons (DX/STD)
```

### Database Schema

#### best_records Table

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

#### recent_records Table

Same structure as `best_records`, stores recent play records.

#### events Table

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

Business event tracking table, automatically created at startup. Records webhook calls, image generation, bind/unbind, sync tasks, and other events. Powers DAU/WAU/MAU and other metric aggregations. Historical records older than 90 days are automatically purged by a background thread.

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
GET /linebot/add_friend?id=<friend_id>
```

#### Admin Dashboard API

```
GET/POST /admin/panel              # Admin login/dashboard
GET      /admin/logout             # Logout
POST     /admin/trigger_update     # Trigger user update
POST     /admin/edit_user          # Edit user data
POST     /admin/delete_user        # Delete user
POST     /admin/get_user_data      # Get user data
POST     /admin/load_nicknames     # Batch load nicknames
POST     /admin/clear_cache        # Clear nickname cache
POST     /admin/cancel_task        # Cancel task
GET      /admin/task_status        # Get task status
GET      /admin/get_logs           # Get logs
```

### Configuration Reference

#### Complete config.json

```json
{
    "admin_password": "secure_pwd",        // Admin panel password
    "maimai_version": {
        "jp": ["PRiSM PLUS", "CiRCLE"],    // JP server current/previous versions
        "intl": ["PRiSM PLUS"]             // International server versions
    },
    "temp_version": {
        "abbr": "CiRCLE",                  // Upcoming version abbreviation
        "title": "CiRCLE"                  // Upcoming version title
    },
    "domain": "your-domain.com",           // Service domain (no protocol)
    "host": "0.0.0.0",                     // Listen address
    "port": 5000,                          // Service port
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
        "bind_token": "AUTO_GENERATED_TOKEN"  // Auto-generated bind token
    },
    "cloudflare_r2": {
        "enabled": false,                      // Enable Cloudflare R2 image storage
        "account_id": "",
        "access_key_id": "",
        "secret_access_key": "",
        "bucket_name": "",
        "public_url": ""
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
ls assets/fonts/line_seed_jietng.ttf

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

**Copyright © 2025 - 2026 Matsuki. All Rights Reserved.**

This software is proprietary. Copying, modification, distribution, or use of this software is strictly prohibited without express written permission from the copyright holder.

See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [LINE Messaging API](https://developers.line.biz/) - Messaging platform
- [Maimai DX](https://maimai.sega.jp/) - Original game by SEGA
- [DXRating](https://github.com/gekichumai/dxrating) - Song data source
- [arcade-songs](https://arcade-songs.zetaraku.dev) - Arcade game song database
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

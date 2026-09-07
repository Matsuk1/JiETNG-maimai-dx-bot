# JiETNG · 舞萌DX 查分器 LINE 机器人

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="100" />

**舞萌DX 查分器 ·『maimai でらっくす』音游成绩追踪与数据管理系统**

同时支持 maimai 日服 (JP) 与国际服 (INTL) · 免费 Rating 计算 · B50 / Best 50 成绩图生成

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.21.0-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

简体中文 | [English](README_EN.md) | [日本語](README_JP.md)

<a href="https://lin.ee/Q6O7aI8"><img src="https://scdn.line-apps.com/n/line_add_friends/btn/ja.png" alt="添加好友" height="36" border="0"></a>

[功能特性](#功能特性) • [命令列表](https://jietng.matsuk1.com/commands/) • [在线文档](https://jietng.matsuk1.com/) • [快速开始](#快速开始) • [管理后台](#管理后台) • [部署指南](#部署指南) • [开发文档](#开发文档)

</div>

---

## 项目简介

**JiETNG** 是一个功能完善的 LINE Bot 服务，为玩家提供成绩追踪、数据分析以及各种游戏辅助功能。支持日服（JP）和国际服（INTL）双版本。

### 核心特性

- **成绩追踪**: 自动同步并存储 Best/Recent 游戏记录
- **数据可视化**: 生成详细的 B50 成绩图表，支持自定义筛选条件
- **好友系统**: 查看好友成绩，管理好友申请
- **排行榜**: DX Rating 用户排名，支持日服/国际服分版本查看
- **版本进度**: 追踪各版本达成情况（极/将/神/舞舞）
- **推歌功能**: 按难度定数随机推荐歌曲
- **位置服务**: 查找附近的 Maimai 游戏厅
- **管理后台**: 功能完善的 Web 管理界面
- **性能优化**: 双队列架构（图片队列/网络队列）配合频率限制
- **多语言支持**: 日语/英语/中文交互界面，多语言文档

---

## 功能特性

### 核心功能

- **账户管理**: SEGA 账户绑定、查看、解绑
- **成绩查询**: B50/B40/B35/B15/AB50/AP50/RCT50/IDEALB50 等多种成绩图
- **高级筛选**: 支持定数、Rating、达成率、DX 分数等多条件组合筛选
- **歌曲查询**: 歌曲信息搜索、个人成绩查询、随机选曲
- **版本达成**: 极/将/神/舞舞牌子达成情况追踪
- **好友功能**: 好友列表、查看好友 B50
- **实用工具**: Rating 计算、分数计算器
- **位置服务**: 发送位置查找附近的 Maimai 游戏厅

### 完整命令列表

详细的命令说明和使用示例请查看 **[在线命令文档](https://jietng.matsuk1.com/commands/)**

---

## 管理后台

基于 Web 的管理界面，提供全面的用户和系统管理功能。

### 访问地址

```
https://your-domain.com/admin/panel
```

### 功能模块

| 模块 | 说明 |
|------|------|
| **用户管理** | 查看所有用户、编辑用户数据、删除用户、触发更新 |
| **实时昵称** | 自动从 LINE SDK 获取并缓存昵称（5分钟缓存） |
| **双队列监控** | 图片队列（3并发）+ 网络队列（1并发） |
| **任务追踪** | 显示最近 20 个完成任务及执行时间统计 |
| **频率限制** | 防止 30 秒内重复请求（每类任务最多 2 个） |
| **业务指标** | DAU/WAU/MAU、粘性分析、今日图片/同步/绑定统计、命令分布、30 天 DAU 趋势图、小时热力图 |
| **系统监控** | CPU/内存使用、队列状态、线程数、运行时长（可折叠） |
| **实时日志** | 查看最近 100 行日志，支持 ANSI 颜色代码 |
| **AI 运维** | 通过受限 Codex + MCP 查询运行状态、错误、用户和内部开发者数据，支持图片诊断及白名单文件维护 |
| **数据刷新** | 快速刷新单个用户数据和昵称 |

### 主要特点

- **延迟加载**: 登录后立即显示页面，昵称异步加载
- **响应式设计**: 完整支持桌面和移动设备
- **双队列架构**: 图片生成和网络任务分离，提高并发性能
- **任务追踪**: 实时显示运行中/排队中/已完成任务及耗时统计
- **业务分析**: 基于 MySQL events 表的事件追踪，DAU/WAU/MAU 等核心指标自动聚合，30 天趋势图、小时分布热力图
- **智能限流**: 保护服务器资源免受快速重复请求影响
- **彩色日志**: ANSI 颜色代码支持，便于识别错误/警告
- **会话管理**: 基于 Cookie 的安全认证
- **状态保持**: 刷新页面后保持当前标签状态

### 配置方法

在 `config.json` 中添加管理员密码：

```json
{
    "admin_password": "your_secure_password"
}
```

AI 运维默认调用服务器上已登录的 `codex`。若 systemd 找不到命令，可设置绝对路径：

```json
{
    "ai_monitor": {
        "enabled": true,
        "codex_command": "/usr/local/bin/codex",
        "model": "",
        "timeout_seconds": 90,
        "session_ttl_seconds": 3600
    }
}
```

也可使用 `JIETNG_CODEX_COMMAND`、`JIETNG_CODEX_MODEL`、`JIETNG_CODEX_TIMEOUT` 和 `JIETNG_CODEX_SESSION_TTL` 环境变量覆盖。后台会懒启动一个常驻 `codex app-server`，同一管理员登录会话复用独立 thread，默认空闲 1 小时后释放；浏览器保留最近 20 条消息，仅用于 app-server 重启后的上下文恢复。常驻 thread 会保留完整连续上下文，并由 Codex 在接近模型上限时自动压缩。若 Gunicorn 的本机监听地址与 `config.json` 中的端口不同，可用 `JIETNG_MONITOR_BRIDGE_URL=http://127.0.0.1:<port>` 指定内部服务地址。

MCP 的开发者数据查询直接走本机数据层，不需要 API token；用户凭据、Cookie 和 token 会被递归脱敏。AI 可以查询最多 90 天的逐日业务指标、用户活动时间线、运行状态、任务队列、结构化日志、数据库、部署、公告及统计、Tip/Ad、备份、DXData、通知、背景、插件与非敏感配置状态。对话支持安全 Markdown、最多 3 张图片输入，以及由模型调用 MCP 完成的裁剪、缩放、旋转、灰度、模糊和图像增强；处理结果通过登录态保护的临时地址返回，不写入项目资源目录。

管理员明确提出操作时，AI 还可触发用户同步、清理昵称缓存/通知、创建备份、更新 DXData，以及创建、更新、发布或删除公告和 Tip/Ad。操作通过仅接受本机回环请求的内部桥接进入正在运行的 Flask 进程；凭据在每个服务进程启动时随机生成且只传给 MCP 子进程，无需写入 `config.json`。任意 SQL、Shell、外部 URL、用户删除、账号绑定、用户字段编辑和开发者 token 管理不会开放给 AI。

AI 请求会先创建后台任务，再由页面轮询结果。iOS 主屏幕 Web App 切到后台或页面被系统重载后，会从本地保存的任务 ID 恢复查询，不要求一条 HTTP 连接持续保持。

文件维护统一由一个 MCP 工具处理，仅允许 `data/dxdata/`、`assets/` 和 `languages/`。它支持目录浏览、UTF-8 文本分段读取、搜索、整文件写入及精确替换；现有文件必须带读取时得到的 SHA-256 才能修改。二进制文件只返回元数据，不支持删除、移动或创建目录。

### 使用方法

1. 访问 `https://your-domain.com/admin/panel`
2. 使用管理员密码登录
3. 在五个主要标签页中导航：
   - **Users**: 用户列表和数据管理
   - **Task Queue**: 双队列监控（图片 + 网络队列）
   - **Statistics**: 业务指标（DAU/WAU/MAU、今日活动统计、趋势图）+ 系统健康监控
   - **Notices**: 公告管理
   - **DXData**: 歌曲数据库管理与更新
   - **Logs**: 实时日志查看器

---

## 快速开始

### 系统要求

- **Python**: 3.10 或更高版本
- **MySQL**: 5.7+ / MariaDB 10.2+
- **操作系统**: Linux / macOS / Windows

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/Matsuk1/JiETNG.git
cd JiETNG
```

#### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

#### 3. 配置数据库

```bash
# 登录 MySQL
mysql -u root -p

# 创建数据库和用户
CREATE DATABASE maimai_records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jietng'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON maimai_records.* TO 'jietng'@'localhost';
FLUSH PRIVILEGES;

# 导入数据库结构
mysql -u jietng -p maimai_records < records_db.sql
```

#### 4. 获取 LINE Channel 凭证

1. 访问 [LINE Developers Console](https://developers.line.biz/)
2. 创建 Messaging API Channel
3. 获取 **Channel Access Token** 和 **Channel Secret**
4. 设置 Webhook URL：`https://your-domain.com/linebot/webhook`
5. 启用 **Use webhook**

#### 5. 配置 config.json

编辑 `config.json` 文件（完整结构参见[配置参考](#完整的-configjson)）：

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

#### 6. 启动服务

```bash
python main.py
```

服务将在 `http://0.0.0.0:<port>` 启动（端口由 config.json 中的 `port` 决定）

### 生产环境部署（推荐）

```bash
gunicorn -w 1 --threads 8 -b 0.0.0.0:5000 --timeout 120 main:app
```

项目的任务队列、管理员会话和 AI thread 都是进程内状态，因此生产环境使用单 worker 加线程；不要直接增加 Gunicorn worker 数量。

---

## 部署指南

### 使用 Docker（推荐）

#### 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libzbar0 \
    libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "--timeout", "120", "main:app"]
```

#### 创建 docker-compose.yml

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

#### 启动容器

```bash
docker-compose up -d
```

### 使用 Systemd（Linux）

创建 `/etc/systemd/system/jietng.service`：

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

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable jietng
sudo systemctl start jietng
```

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 16m;

    location /linebot {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # LINE Webhook 设置
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

启用 HTTPS（推荐）：

```bash
sudo certbot --nginx -d your-domain.com
```

---

## 开发文档

### 项目结构

```
JiETNG/
├── main.py                    # Flask 应用入口
├── config.json                # 配置文件
├── README.md                  # 中文文档（本文件）
├── README_EN.md               # 英文文档
├── README_JP.md               # 日文文档
├── requirements.txt           # Python 依赖
├── records_db.sql             # 数据库结构
├── modules/                   # 功能模块
│   ├── api/                   # Flask API 蓝图与开发者认证
│   ├── backup_manager.py      # 备份管理
│   ├── bindtoken_manager.py   # 绑定 Token 管理
│   ├── commands/              # 命令路由、解析、帮助与配置
│   ├── config_loader.py       # 配置加载器
│   ├── dbpool_manager.py      # 数据库连接池
│   ├── devtoken_manager.py    # 开发者 Token 管理
│   ├── dxdata_manager.py      # 歌曲数据管理
│   ├── event_tracker.py       # 业务事件追踪与指标聚合
│   ├── image_cache.py         # 图像缓存
│   ├── image_manager.py       # 图像处理
│   ├── image_uploader.py      # 图床上传（Imgur/Cloudflare R2）
│   ├── json_encrypt.py        # 加密工具
│   ├── line_messenger.py      # LINE 消息发送
│   ├── maimai_manager.py      # Maimai API 接口
│   ├── memory_manager.py      # 内存管理和清理
│   ├── message_manager.py     # 多语言消息管理
│   ├── message_texts.py       # 多语言消息文本定义
│   ├── notice_manager.py      # 公告系统
│   ├── notice_stats.py        # 公告统计
│   ├── notification_manager.py # 系统通知管理（Web Push）
│   ├── perm_request_generator.py  # 权限请求生成器
│   ├── perm_request_handler.py    # 权限请求处理器
│   ├── rate_limiter.py        # 频率限制 + 请求追踪
│   ├── record_generator.py    # 成绩图生成
│   ├── record_manager.py      # 数据库操作
│   ├── score_recognition/     # 成绩图 OCR 运行时管线与模型
│   ├── song_generator.py      # 歌曲图生成
│   ├── song_matcher.py        # 歌曲搜索（支持模糊匹配）
│   ├── storelist_generator.py # 机厅列表生成（Flex Message）
│   ├── system_checker.py      # 系统自检
│   ├── tip_ad_manager.py      # 更新完成后提示/广告管理
│   └── user_manager.py        # 用户管理 + 昵称缓存
├── templates/                 # HTML 模板
│   ├── admin_login.html       # 管理员登录页
│   ├── admin_panel.html       # 管理后台界面
│   ├── bind_form.html         # 账户绑定表单
│   ├── common_styles.html     # 通用样式
│   ├── error.html             # 错误页面
│   ├── loading.html           # 加载中过渡页面
│   └── success.html           # 成功页面
├── data/                      # 数据文件
│   ├── dxdata/                # 歌曲数据库目录
│   │   ├── dxdata.json        # 歌曲定数数据
│   │   ├── dxdata_version.json # 版本信息
│   │   └── intl_override.csv  # 国际服覆盖数据
│   ├── images/                # 生成的图片缓存
│   ├── backup/                # 数据备份
│   ├── notice.json            # 公告信息
│   ├── tip_ad.json            # 更新提示/广告配置
│   └── user.json.enc          # 用户数据（加密）
└── assets/                    # 静态资源
    ├── fonts/                 # 字体文件
    ├── pics/                  # 图片（logo 等）
    ├── covers/                # 歌曲封面图
    ├── plates/                # 牌子图片
    ├── versions/              # 版本图标
    └── icon/                  # 图标资源
        ├── combo/             # Full Combo 图标
        ├── combo_rcd/         # 成绩页 Combo 图标
        ├── dx_star/           # DX Star 图标
        ├── score/             # 评分等级图标
        ├── sync/              # Full Sync 图标
        ├── sync_rcd/          # 成绩页 Sync 图标
        └── type/              # 谱面类型图标（DX/STD）
```

### 数据库结构

#### best_records 表

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

#### recent_records 表

结构与 `best_records` 相同，存储最近游玩记录。

#### events 表

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

业务事件追踪表，启动时自动创建。记录 webhook 调用、图片生成、绑定/解绑、同步任务等事件，支撑 DAU/WAU/MAU 等指标聚合。超过 90 天的历史记录由后台线程自动清理。

### API 接口

#### Webhook 接收

```
POST /linebot/webhook
Headers:
  X-Line-Signature: <signature>
Body: LINE webhook event JSON
```

#### SEGA 账户绑定

```
GET/POST /linebot/sega_bind?token=<token>
```

#### 好友添加

```
GET /linebot/add_friend?id=<friend_id>
```

#### 管理后台 API

```
GET/POST /admin/panel              # 管理员登录/主页
GET      /admin/logout             # 登出
POST     /admin/trigger_update     # 触发用户更新
POST     /admin/edit_user          # 编辑用户数据
POST     /admin/delete_user        # 删除用户
POST     /admin/get_user_data      # 获取用户数据
POST     /admin/load_nicknames     # 批量加载昵称
POST     /admin/clear_cache        # 清除昵称缓存
GET      /admin/api/overview       # 获取实时概览
GET      /admin/api/hourly         # 获取指定日期活动
GET      /admin/api/tasks          # 获取实时任务队列
GET      /admin/api/users          # 分页获取用户
GET      /admin/get_logs           # 获取日志
POST     /admin/api/ai-monitor/query          # 创建 AI 运维诊断
GET      /admin/api/ai-monitor/query/<job_id> # 查询诊断结果
GET      /admin/api/ai-monitor/image         # 读取诊断图片
```

### 配置参考

#### 完整的 config.json

```json
{
    "admin_password": "secure_pwd",        // 管理后台密码
    "maimai_version": {
        "jp": ["PRiSM PLUS", "CiRCLE"],    // 日服当前/上一版本
        "intl": ["PRiSM PLUS"]             // 国际服当前版本
    },
    "temp_version": {
        "abbr": "CiRCLE",                  // 下一版本缩写（用于临时数据）
        "title": "CiRCLE"                  // 下一版本全名
    },
    "domain": "your-domain.com",           // 服务域名（不含协议）
    "host": "0.0.0.0",                     // 监听地址
    "port": 5000,                          // 服务端口
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
        "bind_token": "AUTO_GENERATED_TOKEN"  // 自动生成的绑定令牌
    },
    "cloudflare_r2": {
        "enabled": false,                      // 是否启用 R2 图床
        "account_id": "",
        "access_key_id": "",
        "secret_access_key": "",
        "bucket_name": "",
        "public_url": ""
    },
    "ai_monitor": {
        "enabled": true,
        "codex_command": "codex",
        "model": "",
        "timeout_seconds": 90,
        "session_ttl_seconds": 3600
    }
}
```

---

## 故障排除

### 常见问题

#### SSL 证书错误

**问题**：`SSL: CERTIFICATE_VERIFY_FAILED`

**解决方案**：
```bash
pip install --upgrade certifi
```

#### 数据库连接失败

**问题**：`Can't connect to MySQL server`

**检查**：
```bash
# 检查 MySQL 状态
sudo systemctl status mysql

# 检查用户权限
mysql -u jietng -p
SHOW GRANTS FOR 'jietng'@'localhost';
```

#### LINE Webhook 验证失败

**问题**：`InvalidSignatureError`

**检查**：
- 确认 config.json 中的 `line_channel.secret` 正确
- 确认 LINE Developers Console 中的 Webhook URL 正确
- 确保已启用 HTTPS（LINE 要求）

#### 图像生成失败

**问题**：缺少字体或图标

**解决方案**：
```bash
# 确认字体文件存在
ls assets/fonts/line_seed_jietng.ttf

# 确认图标目录
ls assets/icon/combo/
ls assets/icon/score/
```

#### 管理后台登录失败

**问题**：密码错误或未配置

**解决方案**：
```json
// 确认 config.json 中存在 admin_password
{
    "admin_password": "your_password"
}
```

```bash
# 重启服务使配置生效
sudo systemctl restart jietng
```

### 日志查看

```bash
# 查看实时日志
tail -f jietng.log

# 使用 systemd
journalctl -u jietng -f
```

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

### 代码规范

- 遵循 PEP 8 编码规范
- 添加类型注解
- 编写文档字符串
- 提交前运行测试（如有）

---

## 许可证

**Copyright © 2025 - 2026 Matsuki. All Rights Reserved.**

本软件为专有软件，保留所有权利。未经版权所有者明确书面许可，严禁复制、修改、分发或使用本软件。

详见 [LICENSE](LICENSE) 文件。

---

## 致谢

- [LINE Messaging API](https://developers.line.biz/) - 消息平台
- [Maimai DX](https://maimai.sega.jp/) - SEGA 原版游戏
- [DXRating](https://github.com/gekichumai/dxrating) - 歌曲数据来源
- [arcade-songs](https://arcade-songs.zetaraku.dev) - 音游歌曲数据库
- 所有贡献者和用户

---

## 联系方式

- **项目地址**：https://github.com/Matsuk1/JiETNG
- **问题反馈**：https://github.com/Matsuk1/JiETNG/issues
- **LINE Bot**：[@299bylay](https://line.me/R/ti/p/@299bylay)

---

<div align="center">

**如果觉得这个项目有帮助，请给个 Star！**

由 [Matsuk1](https://github.com/Matsuk1) 制作

</div>

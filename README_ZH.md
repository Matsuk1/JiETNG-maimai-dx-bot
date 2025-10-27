# JiETNG - Maimai DX LINE Bot

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="100" />

**Maimai DX 音游成绩追踪与数据管理系统**

支持日服和国际服

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.14.5-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | 简体中文

[功能特性](#功能特性) • [快速开始](#快速开始) • [管理后台](#管理后台) • [部署指南](#部署指南) • [开发文档](#开发文档)

</div>

---

## 项目简介

**JiETNG** 是一个功能完善的 Maimai DX LINE Bot 服务，为玩家提供成绩追踪、数据分析以及各种游戏辅助功能。支持日服（JP）和国际服（INTL）双版本。

### 核心特性

- **成绩追踪**: 自动同步并存储 Best/Recent 游戏记录
- **数据可视化**: 生成详细的 B50/B100 成绩图表，支持自定义筛选条件
- **好友系统**: 查看好友成绩，管理好友申请
- **版本进度**: 追踪各版本达成情况（极/将/神/舞舞）
- **推歌功能**: 按难度定数随机推荐歌曲
- **位置服务**: 查找附近的 Maimai 游戏厅
- **数据安全**: SEGA 账户信息使用 Fernet 加密存储
- **管理后台**: 功能完善的 Web 管理界面
- **性能优化**: 双队列架构（图片队列/网络队列）配合频率限制
- **多语言支持**: 日语交互界面，中英文文档

---

## 功能特性

### 账户管理

| 功能 | 命令 | 说明 |
|------|------|------|
| 绑定账户 | `segaid bind` | 将 SEGA 账户绑定到 LINE |
| 查看绑定 | `getme` | 显示当前账户绑定状态 |
| 解除绑定 | `unbind` | 移除账户绑定 |

### 成绩查询

#### 成绩图类型

| 命令 | 说明 |
|------|------|
| `b50` / `best 50` | 标准 B50（旧谱35 + 新谱15） |
| `b100` / `best 100` | B100（旧谱70 + 新谱30） |
| `b35` / `b15` | 单独查看旧谱/新谱 |
| `ab50` / `all best 50` | 不分新旧谱的全部 B50 |
| `apb50` | 仅显示 AP/APP 的 B50 |
| `idealb50` | 理论最高分的 B50 |
| `rct50` / `r50` | 最近 50 次游玩记录 |

#### 高级筛选

支持多条件组合筛选：

```
b50 -lv 14.0 14.9    # 筛选定数 14.0-14.9
b50 -ra 200 250      # 筛选 rating 200-250
b50 -scr 99.5        # 筛选达成率 ≥99.5%
b50 -dx 95           # 筛选 DX 分数 ≥95%
```

### 歌曲查询

| 命令格式 | 示例 | 说明 |
|---------|------|------|
| `[曲名]ってどんな曲` | `オンゲキってどんな曲` | 搜索歌曲信息 |
| `[曲名]のレコード` | `オンゲキのレコード` | 查看个人成绩 |
| `ランダム曲 [定数]` | `ランダム曲 14+` | 随机推荐歌曲 |
| `[定数]のレコードリスト` | `14+のレコードリスト` | 查看定数成绩列表 |

### 版本达成

| 命令 | 说明 |
|------|------|
| `[版本]極の達成状況` | 查看"极"达成进度 |
| `[版本]将の達成状況` | 查看"将"达成进度 |
| `[版本]神の達成状況` | 查看"神"达成进度 |
| `[版本]舞舞の達成状況` | 查看"舞舞"达成进度 |

版本缩写示例：`真`、`超`、`晓`、`祭`、`煌`、`镜` 等

### 好友功能

| 命令 | 说明 |
|------|------|
| `friend list` | 显示好友列表 |
| `friend-b50 [好友码]` | 查看好友的 B50 |
| `add-friend [好友码]` | 发送好友申请 |
| `maid card` / `maid` | 生成带二维码的个人名片 |

### 实用工具

| 命令 | 说明 |
|------|------|
| `maimai update` | 从服务器更新成绩数据 |
| `rc [定数]` | 查看 Rating 对照表 |
| `calc [tap] [hold] [slide] [touch] [break]` | 计算理论分数 |
| `yang` / `yra` | 查看 Yang Rating |
| `[版本]のバージョンリスト` | 查看版本歌曲列表 |

### 位置服务

向 Bot 发送位置信息，自动查找附近的 Maimai 游戏厅并提供地图链接。

---

## 管理后台

基于 Web 的管理界面，提供全面的用户和系统管理功能。

### 访问地址

```
https://your-domain.com/linebot/admin
```

### 功能模块

| 模块 | 说明 |
|------|------|
| **用户管理** | 查看所有用户、编辑用户数据、删除用户、触发更新 |
| **实时昵称** | 自动从 LINE SDK 获取并缓存昵称（5分钟缓存） |
| **双队列监控** | 图片队列（3并发）+ 网络队列（1并发） |
| **任务追踪** | 显示最近 20 个完成任务及执行时间统计 |
| **频率限制** | 防止 30 秒内重复请求（每类任务最多 2 个） |
| **系统统计** | 用户数、版本分布、CPU/内存使用、队列状态、运行时长 |
| **实时日志** | 查看最近 100 行日志，支持 ANSI 颜色代码 |
| **数据刷新** | 快速刷新单个用户数据和昵称 |

### 主要特点

- **延迟加载**: 登录后立即显示页面，昵称异步加载
- **响应式设计**: 完整支持桌面和移动设备
- **双队列架构**: 图片生成和网络任务分离，提高并发性能
- **任务追踪**: 实时显示运行中/排队中/已完成任务及耗时统计
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

### 使用方法

1. 访问 `https://your-domain.com/linebot/admin`
2. 使用管理员密码登录
3. 在五个主要标签页中导航：
   - **Users**: 用户列表和数据管理
   - **Task Queue**: 双队列监控（图片 + 网络队列）
   - **Statistics**: 系统统计信息
   - **Notices**: 公告管理
   - **Logs**: 实时日志查看器

---

## 快速开始

### 系统要求

- **Python**: 3.8 或更高版本
- **MySQL**: 5.7+ / MariaDB 10.2+
- **操作系统**: Linux / macOS / Windows

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/Matsuk1/JiETNG.git
cd JiETNG
```

#### 2. 安装依赖

```bash
pip install -r inits/requirements.txt
```

#### 3. 配置数据库

```bash
# 登录 MySQL
mysql -u root -p

# 创建数据库和用户
CREATE DATABASE records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'jietng'@'localhost' IDENTIFIED BY 'jietng_2025';
GRANT ALL PRIVILEGES ON records.* TO 'jietng'@'localhost';
FLUSH PRIVILEGES;

# 导入数据库结构
mysql -u jietng -p records < inits/records_db.sql
```

#### 4. 配置 config.json

编辑 `config.json` 文件：

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

#### 5. 获取 LINE Channel 凭证

1. 访问 [LINE Developers Console](https://developers.line.biz/)
2. 创建 Messaging API Channel
3. 获取 **Channel Access Token** 和 **Channel Secret**
4. 设置 Webhook URL：`https://your-domain.com/linebot/webhook`
5. 启用 **Use webhook**

#### 6. 启动服务

```bash
python main.py
```

服务将在 `http://0.0.0.0:5100` 启动

### 生产环境部署（推荐）

```bash
gunicorn -w 4 -b 0.0.0.0:5100 --timeout 120 main:app
```

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
COPY inits/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 5100

# 启动命令
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5100", "--timeout", "120", "main:app"]
```

#### 创建 docker-compose.yml

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

    location /linebot {
        proxy_pass http://127.0.0.1:5100;
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
├── README.md                  # 英文文档
├── README_ZH.md               # 中文文档（本文件）
├── inits/                     # 初始化文件
│   ├── requirements.txt       # Python 依赖
│   └── records_db.sql         # 数据库结构
├── modules/                   # 功能模块
│   ├── config_loader.py       # 配置加载器
│   ├── db_pool.py             # 数据库连接池
│   ├── user_console.py        # 用户管理 + 昵称缓存
│   ├── maimai_console.py      # Maimai API 接口
│   ├── record_console.py      # 数据库操作
│   ├── record_generate.py     # 成绩图生成
│   ├── song_generate.py       # 歌曲图生成
│   ├── img_console.py         # 图像处理
│   ├── img_cache.py           # 图像缓存
│   ├── img_upload.py          # 图床上传
│   ├── token_console.py       # Token 管理
│   ├── friend_list.py         # 好友界面
│   ├── notice_console.py      # 通知系统
│   ├── dxdata_console.py      # 歌曲数据管理
│   ├── note_score.py          # 分数计算
│   ├── json_encrypt.py        # 加密工具
│   ├── rate_limiter.py        # 频率限制 + 请求追踪
│   ├── line_messenger.py      # LINE 消息发送
│   ├── song_matcher.py        # 歌曲搜索（支持模糊匹配）
│   ├── memory_manager.py      # 内存管理和清理
│   ├── system_check.py        # 系统自检
│   └── reply_text.py          # 消息模板
├── templates/                 # HTML 模板
│   ├── bind_form.html         # 账户绑定表单
│   ├── success.html           # 成功页面
│   ├── error.html             # 错误页面
│   ├── admin_login.html       # 管理员登录页
│   ├── admin_panel.html       # 管理后台界面
│   └── stats.html             # 统计信息页面
├── data/                      # 数据文件
│   ├── dxdata.json            # 歌曲数据库
│   ├── notice.json            # 公告信息
│   ├── re_dxdata.csv          # 区域数据
│   └── user.json.enc          # 用户数据（加密）
└── assets/                    # 静态资源
    ├── fonts/                 # 字体文件
    ├── pics/                  # 图片
    └── icon/                  # 图标资源
```

### 数据库结构

#### best_records 表

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

#### recent_records 表

结构与 `best_records` 相同，存储最近游玩记录。

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
GET /linebot/add_friend?code=<friend_code>
```

#### 管理后台 API

```
GET/POST /linebot/admin                    # 管理员登录/主页
GET      /linebot/admin/logout             # 登出
POST     /linebot/admin/trigger_update     # 触发用户更新
POST     /linebot/admin/edit_user          # 编辑用户数据
POST     /linebot/admin/delete_user        # 删除用户
POST     /linebot/admin/get_user_data      # 获取用户数据
POST     /linebot/admin/load_nicknames     # 批量加载昵称
POST     /linebot/admin/clear_cache        # 清除昵称缓存
POST     /linebot/admin/cancel_task        # 取消任务
GET      /linebot/admin/task_status        # 获取任务状态
GET      /linebot/admin/get_logs           # 获取日志
GET      /linebot/admin/memory_stats       # 获取内存统计
POST     /linebot/admin/trigger_cleanup    # 手动触发内存清理
```

### 配置参考

#### 完整的 config.json

```json
{
    "admin_id": ["U0123..."],              // LINE 管理员用户 ID
    "admin_password": "secure_pwd",        // 管理后台密码
    "maimai_version": {
        "jp": ["PRiSM PLUS", "CiRCLE"],    // 日服版本
        "intl": ["PRiSM PLUS"]             // 国际服版本
    },
    "domain": "jietng.example.com",        // 服务域名
    "port": 5100,                          // 服务端口
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
        "user_data": "AUTO_GENERATED_KEY",     // 自动生成的 Fernet 密钥
        "bind_token": "AUTO_GENERATED_TOKEN"   // 自动生成的绑定令牌
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
ls assets/fonts/mplus-jietng.ttf

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

本项目采用 [MIT License](LICENSE) 许可证。

---

## 致谢

- [LINE Messaging API](https://developers.line.biz/) - 消息平台
- [Maimai DX](https://maimai.sega.jp/) - SEGA 原版游戏
- [DXRating](https://github.com/gekichumai/dxrating) - 歌曲数据来源
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

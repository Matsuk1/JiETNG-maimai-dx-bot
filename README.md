# JiETNG - Maimai DX LINE Bot

<div align="center">

<img src="./assets/pics/logo.png" alt="Logo" width="150" />

**【日服/国际服】Maimai DX 音游成绩追踪与数据管理 LINE Bot**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1.0-green.svg)](https://flask.palletsprojects.com/)
[![LINE Bot SDK](https://img.shields.io/badge/LINE_Bot_SDK-3.14.5-00C300.svg)](https://github.com/line/line-bot-sdk-python)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用指南](#使用指南) • [部署指南](#部署指南) • [开发文档](#开发文档)

</div>

---

## 📖 简介

**JiETNG** 是一个功能强大的 Maimai DX LINE Bot 服务，为玩家提供成绩追踪、数据分析等全方位功能。支持日服(JP)和国际服(INTL)双版本。

### 核心特色

- 🎯 **成绩追踪**: 自动同步并存储您的 Best/Recent 游戏记录
- 📊 **数据可视化**: 生成精美的 B50/B100 成绩图表
- 👥 **好友系统**: 查看好友成绩,发起好友申请
- 🏆 **版本达成**: 查看各版本称号进度(极/将/神/舞舞)
- 🎲 **随机推歌**: 按定数随机推荐歌曲
- 🗺️ **附近店铺**: 基于位置查找附近的 Maimai 游戏厅
- 🔒 **数据安全**: SEGA 账户信息采用 Fernet 加密存储

---

## 功能特性

### 1. 账户管理

| 功能 | 命令 | 说明 |
|------|------|------|
| 绑定账户 | `segaid bind` | 绑定 SEGA 账户 |
| 查看绑定 | `getme` | 查看当前绑定状态 |
| 解除绑定 | `unbind` | 解除账户绑定 |

### 2. 成绩查询

#### 成绩图类型

| 命令 | 说明 |
|------|------|
| `b50` / `best 50` | 标准 B50 (旧谱35 + 新谱15) |
| `b100` / `best 100` | B100 (旧谱70 + 新谱30) |
| `b35` / `b15` | 单独查看旧谱/新谱 |
| `ab50` / `all best 50` | 不分新旧谱的全部 B50 |
| `apb50` | AP/APP 专属 B50 |
| `idealb50` | 理想分数下的 B50 |
| `rct50` / `r50` | 最近50次游玩记录 |

#### 高级筛选

支持多条件组合筛选:

```
b50 -lv 14.0 14.9    # 筛选定数 14.0~14.9
b50 -ra 200 250      # 筛选 rating 200~250
b50 -scr 99.5        # 筛选达成率 ≥99.5%
b50 -dx 95           # 筛选 DX 分数 ≥95%
```

### 3. 歌曲查询

| 命令格式 | 示例 | 说明 |
|---------|------|------|
| `[曲名]ってどんな曲` | `オンゲキってどんな曲` | 搜索歌曲信息 |
| `[曲名]のレコード` | `オンゲキのレコード` | 查看个人成绩 |
| `ランダム曲 [定数]` | `ランダム曲 14+` | 随机推歌 |
| `[定数]のレコードリスト` | `14+のレコードリスト` | 查看定数成绩列表 |

### 4. 版本达成

| 命令 | 说明 |
|------|------|
| `[版本]極の達成状況` | 極牌 达成表 |
| `[版本]将の達成状況` | 将牌 达成表 |
| `[版本]神の達成状況` | 神牌 达成表 |
| `[版本]舞舞の達成状況` | 舞舞牌 达成表 |

版本缩写示例: `真`, `超`, `晓`, `祭`, `煌`, `镜` 等

### 5. 好友功能

| 命令 | 说明 |
|------|------|
| `friend list` | 查看好友列表 |
| `friend-b50 [好友码]` | 查看好友 B50 |
| `add-friend [好友码]` | 发送好友申请 |
| `maid card` / `maid` | 生成个人名片(含 QR 码) |

### 6. 工具功能

| 命令 | 说明 |
|------|------|
| `maimai update` | 更新成绩数据 |
| `rc [定数]` | 查看 Rating 对照表 |
| `calc [tap] [hold] [slide] [touch] [break]` | 计算理论分数 |
| `yang` / `yra` | 查看 Yang Rating |
| `[版本]のバージョンリスト` | 查看版本歌曲列表 |

### 7. 位置服务

发送位置信息给 Bot,自动查找附近的 Maimai 游戏厅(含地图链接)

---

## 快速开始

### 系统要求

- **Python**: 3.8 或更高版本
- **MySQL**: 5.7+ / MariaDB 10.2+
- **操作系统**: Linux / macOS / Windows

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/jietng.git
cd jietng
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

编辑 `config.json` 文件,填入以下配置:

```json
{
    "admin_id": ["U0123456789abcdef"],
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
        "dxdata": "https://raw.githubusercontent.com/gekichumai/dxrating/refs/heads/main/packages/dxdata/dxdata.json",
        "proxy": "https://your-proxy-url.com/reply"
    }
}
```

#### 5. 获取 LINE Channel 凭证

1. 访问 [LINE Developers Console](https://developers.line.biz/)
2. 创建 Messaging API Channel
3. 获取 **Channel Access Token** 和 **Channel Secret**
4. 设置 Webhook URL: `https://your-domain.com/linebot/webhook`
5. 启用 **Use webhook**

#### 6. 启动服务

```bash
python main.py
```

服务将在 `http://0.0.0.0:5100` 启动

### 使用 Gunicorn 部署(推荐)

```bash
gunicorn -w 4 -b 0.0.0.0:5100 --timeout 120 main:app
```

---

## 使用指南

### 绑定 SEGA 账户

1. 添加 JiETNG 为 LINE 好友
2. 发送 `segaid bind`
3. 点击链接,输入 SEGA ID 和密码
4. 选择服务器版本(日服/国际服)
5. 绑定成功后,发送 `maimai update` 更新数据

### 查看成绩

```
maimai update           # 更新数据
b50                     # 查看 B50
b50 -lv 14.0 14.9      # 查看定数 14.0~14.9 的 B50
idealb50                # 查看理想分数下的 B50
```

### 好友功能

1. 发送 `maid card` 生成个人名片
2. 分享名片给好友
3. 好友扫描二维码或发送图片给 Bot
4. 自动发送好友申请

### 版本达成

```
宴極の達成状況          # 查看 宴极 达成情况
祭将の達成状況          # 查看 祭将 达成情况
```

---

## 部署指南

### 使用 Docker (推荐)

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

# 复制依赖文件
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

### 使用 Systemd (Linux)

创建 `/etc/systemd/system/jietng.service`:

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

启动服务:

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

        # LINE Webhook 需要的设置
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
```

启用 HTTPS (推荐):

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
├── CODE_REPORT.md             # 代码分析报告
├── README.md                  # 本文档
├── inits/                     # 初始化文件
│   ├── requirements.txt       # Python 依赖
│   └── records_db.sql         # 数据库结构
├── modules/                   # 功能模块
│   ├── config_loader.py       # 配置加载
│   ├── user_console.py        # 用户管理
│   ├── maimai_console.py      # Maimai API
│   ├── record_console.py      # 数据库操作
│   ├── record_generate.py     # 成绩图生成
│   ├── song_generate.py       # 歌曲图生成
│   ├── img_console.py         # 图像处理
│   ├── img_upload.py          # 图床上传
│   ├── token_console.py       # Token 管理
│   ├── friend_list.py         # 好友界面
│   ├── notice_console.py      # 通知系统
│   ├── dxdata_console.py      # 歌曲数据
│   ├── admin_tools.py         # 管理工具
│   ├── note_score.py          # 分数计算
│   ├── json_encrypt.py        # 加密工具
│   └── reply_text.py          # 消息模板
├── proxy/                     # 代理服务
│   ├── config.py              # 代理配置
│   └── jietng_proxy.py        # 代理处理
├── templates/                 # HTML 模板
│   ├── bind_form.html         # 绑定表单
│   ├── success.html           # 成功页面
│   └── error.html             # 错误页面
├── data/                      # 数据文件
│   ├── dxdata.json            # 歌曲数据
│   ├── notice.json            # 通知数据
│   ├── re_dxdata.csv          # 区域数据
│   └── user.json.enc          # 用户数据(加密)
└── assets/                    # 静态资源
    ├── fonts/                 # 字体文件
    ├── pics/                  # 图片
    └── icon/                  # 图标资源
        ├── combo/             # Combo 图标
        ├── score/             # 分数图标
        ├── sync/              # Sync 图标
        ├── dx_star/           # DX 星图标
        └── kind/              # 类型图标
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

结构同 `best_records`,存储最近游玩记录。

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

### 扩展开发

#### 添加新命令

编辑 `main.py` 的 `handle_text_message_task` 函数:

```python
# 添加到 COMMAND_MAP
COMMAND_MAP = {
    "your_command": lambda: your_function(),
    ...
}

# 或添加到 SPECIAL_RULES
SPECIAL_RULES = [
    (lambda msg: msg.startswith("your_pattern"),
     lambda msg: your_handler(msg)),
    ...
]
```

#### 添加新模块

1. 在 `modules/` 创建 `your_module.py`
2. 在 `main.py` 导入:
```python
from modules.your_module import *
```

#### 配置其它服务代理转发
1. 请自行阅读 `proxy_forward.py`
2. 该功能可提供
   - QQ 转发至 LINE
   - Telegram 转发至 LINE
   - Matrix 转发至 LINE
等服务代理

---

## 配置说明

### config.json 完整配置

```json
{
    "admin_id": ["U0123..."],         // LINE 管理员 ID 列表
    "maimai_version": {
        "jp": ["PRiSM PLUS", "CiRCLE"],     // 日服新版本
        "intl": ["PRiSM PLUS"]              // 国际服新版本
    },
    "domain": "jietng.example.com",   // 服务域名
    "port": 5100,                     // 服务端口
    "file_path": {
        "dxdata_list": "./data/dxdata.json",
        "re_dxdata_list": "./data/re_dxdata.csv",
        "user_list": "./data/user.json.enc",
        "notice_file": "./data/notice.json",
        "font": "./assets/fonts/mplus-1p-regular.ttf",
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
        "dxdata": "https://raw.githubusercontent.com/.../dxdata.json",
        "proxy": "https://your-proxy.com/reply"
    },
    "line_channel": {
        "account_id": "@yourlineid",
        "access_token": "YOUR_TOKEN",
        "secret": "YOUR_SECRET"
    },
    "keys": {
        "user_data": "AUTO_GENERATED_KEY",    // 自动生成
        "bind_token": "AUTO_GENERATED_TOKEN"  // 自行选择
    }
}
```

---

## 故障排除

### 常见问题

#### 1. SSL 证书错误

**问题**: `SSL: CERTIFICATE_VERIFY_FAILED`

**解决**:
```bash
pip install --upgrade certifi
```

#### 2. 数据库连接失败

**问题**: `Can't connect to MySQL server`

**检查**:
```bash
# 检查 MySQL 是否运行
sudo systemctl status mysql

# 检查用户权限
mysql -u jietng -p
SHOW GRANTS FOR 'jietng'@'localhost';
```

#### 3. LINE Webhook 验证失败

**问题**: `InvalidSignatureError`

**检查**:
- config.json 中的 `line_channel.secret` 是否正确
- LINE Developers Console 中的 Webhook URL 是否正确
- 是否启用了 HTTPS (LINE 要求)

#### 4. 图像生成失败

**问题**: 缺少字体或图标

**解决**:
```bash
# 确保字体文件存在
ls assets/fonts/mplus-1p-regular.ttf

# 确保图标目录完整
ls assets/icon/combo/
ls assets/icon/score/
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

欢迎提交 Issue 和 Pull Request!

### 开发流程

1. Fork 本项目
2. 创建特性分支: `git checkout -b feature/your-feature`
3. 提交更改: `git commit -am 'Add some feature'`
4. 推送分支: `git push origin feature/your-feature`
5. 提交 Pull Request

### 代码规范

- 遵循 PEP 8 编码规范
- 添加类型注解
- 编写文档字符串
- 提交前运行测试(如有)

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

---

## 🙏 致谢

- [LINE Messaging API](https://developers.line.biz/)
- [Maimai DX](https://maimai.sega.jp/)
- [DXRating](https://github.com/gekichumai/dxrating) - 歌曲数据来源
- 所有贡献者和用户

---

## 📧 联系方式

- **项目主页**: https://github.com/Matsuk1/JiETNG
- **Issues**: https://github.com/Matsuk1/JiETNG/issues
- **LINE Bot**: [@299bylay](https://line.me/R/ti/p/@299bylay)

---

<div align="center">

**如果觉得这个项目有帮助,请给个 ⭐ Star!**

Made with ❤️ by [Matsuk1](https://github.com/Matsuk1)

</div>

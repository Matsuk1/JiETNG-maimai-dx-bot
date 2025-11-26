# JiETNG Telegram Bot

通过 Telegram Bot 调用 JiETNG API 来管理 maimai 账户。

## 功能特性

### 用户命令
- `/start` - 显示欢迎信息和帮助
- `/register` - 注册新用户并获取绑定链接
- `/myinfo` - 查看个人信息
- `/update` - 更新个人数据
- `/b50 [筛选参数]` - 生成 Best 50 图片（支持筛选参数，如 `-lv 14 15`）
- `/search <歌名>` - 搜索歌曲（生成图片展示封面）
- `/versions` - 查看所有 maimai 版本

### 管理员命令
- `/users` - 查看所有用户列表
- `/deleteuser <user_id>` - 删除指定用户

### 图片生成

本项目使用 JiETNG 的图片生成模块，支持：
- Best 50/Best 35/Best 15 等成绩图片（详细卡片展示）
- 搜索结果图片（封面网格展示）
- 自动下载和缓存图标、封面等资源

## 快速开始

### 1. 安装依赖

```bash
pip3 install -r requirements.txt
```

### 2. 配置

编辑 `config.json` 文件：

```json
{
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN_HERE",
    "admin_user_ids": [123456789]
  },
  "api": {
    "base_url": "https://jietng.matsuki.top/api/v1",
    "token": "YOUR_API_TOKEN_HERE"
  }
}
```

**配置说明：**
- `bot_token`: 从 [@BotFather](https://t.me/BotFather) 获取的 Telegram Bot Token
- `admin_user_ids`: 管理员的 Telegram User ID 列表（可以使用 [@userinfobot](https://t.me/userinfobot) 获取）
- `base_url`: JiETNG API 的基础 URL
- `token`: JiETNG API Token

### 3. 运行 Bot

```bash
python3 bot.py
```

## 文件结构

```
JiETNG-Telegram-Bot/
├── bot.py                  # 主程序（Bot 逻辑）
├── api_client.py           # API 客户端（封装所有 API 调用）
├── image_generator.py      # 图片生成（b50, 搜索结果）
├── modules/                # JiETNG 图片生成模块
│   ├── config_loader.py    # 配置加载（路径定义）
│   ├── image_cache.py      # 图片缓存和下载
│   ├── image_manager.py    # 图片管理工具
│   └── record_generator.py # 成绩图片生成
├── assets/                 # 资源文件
│   ├── fonts/              # 字体文件
│   ├── pics/               # 图片（Logo等）
│   └── icon/               # 图标缓存目录
├── data/                   # 数据目录
│   └── covers/             # 封面缓存目录
├── config.json             # 配置文件
├── requirements.txt        # Python 依赖
└── README.md              # 说明文档
```

## 使用示例

### 注册账户
```
/register
```
Bot 会自动创建账户并返回绑定链接，点击链接完成 SEGA 账户绑定。

### 查看信息
```
/myinfo
```

### 查看 Best 50
```
/best50
```

### 带筛选的 Best 50
```
/best50 -lv 14 15
```
只显示 14 和 15 级的歌曲。

### 搜索歌曲
```
/search freedom
```

### 管理员查看所有用户
```
/users
```

### 管理员删除用户
```
/deleteuser U123456789
```

## API 调用示例

Bot 使用 `api_client.py` 来调用 JiETNG API：

```python
from api_client import JiETNGAPIClient

# 初始化客户端
api_client = JiETNGAPIClient(
    base_url="https://jietng.matsuki.top/api/v1",
    token="YOUR_TOKEN"
)

# 创建用户
result = api_client.create_user(
    user_id="U123456789",
    nickname="Test User",
    language="zh"
)

# 获取用户信息
result = api_client.get_user("U123456789")

# 搜索歌曲
result = api_client.search_songs(query="freedom", ver="jp")
```

## 注意事项

1. **User ID 格式**：Telegram Bot 会自动将 Telegram User ID 转换为 JiETNG 格式（添加 `U` 前缀）
2. **管理员权限**：需要在 `config.json` 中配置管理员 User ID 才能使用管理员命令
3. **API Token**：确保使用有效的 JiETNG API Token
4. **绑定链接有效期**：绑定链接在 2 分钟后过期，请尽快完成绑定

## 开发说明

### API 客户端 (api_client.py)

封装了所有 JiETNG API 调用：
- 用户管理（创建、查询、删除、更新）
- 记录管理（获取成绩）
- 歌曲搜索
- 版本查询

### Bot 逻辑 (bot.py)

使用 `python-telegram-bot` 库实现：
- 命令处理器
- 权限控制
- 错误处理
- 交互式回复

## 故障排除

### Bot 无法启动
- 检查 `config.json` 中的 `bot_token` 是否正确
- 确保安装了所有依赖：`pip3 install -r requirements.txt`

### API 调用失败
- 检查 `config.json` 中的 API `token` 是否有效
- 检查 `base_url` 是否正确
- 查看 Bot 日志中的错误信息

### 用户注册失败
- 确保 API Token 有 `/users` 端点的访问权限
- 检查网络连接

## License

MIT License

# Project JiETNG

JiETNG 是一个基于 Python 的 Maimai 查分器 服务端程序，本指南介绍如何在本地或服务器上配置并运行该项目。

---

## 📦 安装依赖

首先确保系统已安装 **Python 3.8+**。  
然后进入项目目录，安装依赖：

```bash
pip3 install -r requirements.txt
```

---

## ⚙️ 配置文件

所有配置均写在 `config.json` 文件中。请根据需要填写以下字段：  
（未提及的部分默认不用修改）

```json
{
  "admin_id": "",
  "domain": "",
  "port": 5000,
  "record_database": {
    "host": "",
    "user": "",
    "password": "",
    "database": ""
  },
  "urls": {
    "line_adding": "",
    "proxy": ""
  },
  "line_channel": {
    "access_token": "",
    "secret": ""
  },
  "keys": {
    "user_data": "",
    "bind_token": ""
  }
}
```

### 字段说明

- **admin_id**  
  填写你自己的 LINE 账户 ID（U 开头的一串字符串）。  
  如果不清楚，可以运行服务后输入 `getme` 来获取。

- **domain**  
  填写运行该服务的服务器（子）域名，例如：  
  ```
  jietng.example.com
  ```

- **port**  
  填写该服务监听的端口号，例如 `5000`。

- **record_database**  
  配置服务所使用的数据库信息：  
  - `host`: 数据库地址  
  - `user`: 数据库用户名  
  - `password`: 数据库密码  
  - `database`: 数据库名称  

- **urls**  
  配置可选的外部链接：  
  - `line_adding`: LINE 账号的加好友链接  
  - `proxy`: 其它服务端转发的链接（如无可不填）

- **line_channel**  
  填写你在 LINE Developers 平台申请的 channel 信息： 
  - `access_token`: Channel access token   
  - `secret`: Channel secret  

- **keys**  
  - `user_data`: 需生成一个 **32 位 base64 编码字符串**，作为用户数据加密密钥  
    > 生成方式示例：  
    > ```bash
    > python3 -c "import base64,os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
    > ```
  - `bind_token`: 随便填写一个字符串即可，用于用户绑定校验。

---

## 🚀 运行服务

配置完成后，可以直接启动：

```bash
python3 main.py
```

若需要后台运行，推荐使用 `systemd` 或 `pm2` 等进程管理工具。

---

## 🔧 使用 systemd 管理 JiETNG

在 Linux 服务器上，可以创建一个 systemd 服务单元文件 `/etc/systemd/system/jietng.service`：

```ini
[Unit]
Description=JiETNG Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/jietng
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

保存后执行以下命令启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable jietng.service
sudo systemctl start jietng.service
```

查看运行状态：

```bash
sudo systemctl status jietng.service
```

查看日志：

```bash
journalctl -u jietng.service -f
```

---

## 🌐 Nginx 反向代理 + HTTPS 配置

如果你希望通过域名直接访问 JiETNG，可以在 Nginx 中配置反向代理。  
以下示例假设：  
- JiETNG 服务运行在本地端口 `5000`  
- 域名是 `jietng.example.com`
- 使用 [Certbot](https://certbot.eff.org/) 获取 SSL 证书  

配置文件 `/etc/nginx/sites-available/jietng.conf`：

```nginx
server {
    listen 80;
    server_name jietng.example.com;

    # 自动跳转到 https
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name jietng.example.com;

    # SSL 证书（使用 Certbot 申请后路径类似）
    ssl_certificate /etc/letsencrypt/live/jietng.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/jietng.example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置并重启 Nginx：

```bash
sudo ln -s /etc/nginx/sites-available/jietng.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## ✅ 检查配置是否成功

1. 服务启动后，终端或日志应输出运行端口和状态信息。  
2. 使用 LINE 添加你的 bot，测试是否能正常响应。  
3. 管理员可通过 `admin_id` 使用特定命令（如 `getme`）验证绑定是否生效。  
4. 在浏览器访问 `https://jietng.example.com/adding`，确认是否能跳转到添加 LINE 账号界面，若能则正确代理到服务。

---

## 📖 附注

- 若数据库尚未建立，请先根据项目提供的 SQL 脚本或手动建表。  
- 域名与端口需保证能被外部访问，必要时配置 **Nginx 反向代理 + HTTPS**。  
- `config.json` 中未提及的部分默认不用修改。
- 项目默认使用 `/linebot/` 来接收 LINE 消息，故请在 **Webhook URL** 处填写 `https://jietng.example.com/linebot/`

---

# JiETNG 部署与运行报告（2025-10-04）

## 环境信息
- 系统：Ubuntu 24.04 LTS（容器环境）
- Python：3.11.12
- 关键依赖：按 `inits/requirements.txt` 安装
- 数据库：MariaDB 10.11.13（兼容 MySQL）

## 部署步骤
1. **安装 Python 依赖**
   ```bash
   pip3 install -r inits/requirements.txt
   ```
2. **安装并启动 MariaDB**
   ```bash
   apt-get update
   DEBIAN_FRONTEND=noninteractive apt-get install -y mariadb-server
   service mariadb start
   ```
3. **初始化数据库与账户**
   ```bash
   mysql -uroot -e "CREATE DATABASE records CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"
   mysql -uroot -e "CREATE USER 'jietng'@'localhost' IDENTIFIED BY 'jietng_2025';"
   mysql -uroot -e "GRANT ALL PRIVILEGES ON records.* TO 'jietng'@'localhost'; FLUSH PRIVILEGES;"
   mysql -ujietng -pjietng_2025 records < inits/records_db.sql
   ```
4. **启动服务**
   ```bash
   python3 main.py
   ```
   Flask 默认监听 `http://127.0.0.1:5000`，终端输出表明应用成功运行。

## 模拟运行与基础功能检查

1. **配置健壮性**：`modules/config_loader.py` 现在会在首次启动时自动生成合法的 `Fernet` 密钥，并为缺失的 `bind_token` 生成随机字符串，避免因为示例配置导致的运行时错误。
2. **语法检查**：
   ```bash
   python3 -m compileall modules main.py
   ```
   所有模块均可成功编译为字节码，未发现语法错误。
3. **Flask 服务冒烟测试**：
   ```bash
   python3 main.py
   ```
   - `/linebot/add`：返回 `302` 跳转到配置中的 LINE 加好友链接。
   - `/linebot/sega_bind?token=test`：由于示例 token 无效，返回 `400` 并渲染错误页面，证明路由与模板加载正常。

## 数据表创建情况
`inits/records_db.sql` 会在 `records` 数据库中创建以下表：
- `best_records`
- `recent_records`

可使用如下命令验证：
```bash
mysql -ujietng -pjietng_2025 -e "USE records; SHOW TABLES;"
```

## 后续建议
- 按需修改 `config.json` 中的域名、LINE 渠道与密钥。
- 生产环境建议改用 `gunicorn`/`uWSGI` 等 WSGI 服务，并结合 Nginx 做反向代理与 HTTPS。
- 建议为 MariaDB 配置 root 密码与远程访问策略，确保安全性。


# Deployment Guide

This guide explains how to deploy the JiETNG Telegram Bot on GitHub Actions or other platforms.

## Option 1: GitHub Actions (Recommended)

Run the bot directly on GitHub's infrastructure using GitHub Actions.

### Advantages
- ✅ **Free** - GitHub Actions provides free compute hours
- ✅ **Secure** - Secrets are encrypted and never exposed
- ✅ **No server needed** - Runs in the cloud
- ✅ **Auto-restart** - Automatically restarts if it crashes

### Setup Steps

#### 1. Fork or Clone the Repository

Fork this repository or push the `telegram` branch to your own GitHub repository.

#### 2. Configure GitHub Secrets

Go to your repository's **Settings → Secrets and variables → Actions** and add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot token from @BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `ADMIN_USER_IDS` | Comma-separated admin user IDs | `123456789, 987654321` |
| `API_BASE_URL` | JiETNG API base URL | `https://jietng.matsuki.top/api/v1` |
| `API_TOKEN` | Your JiETNG API token | `jt_abc123def456...` |

**How to get your Telegram User ID:**
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID

**How to get JiETNG API token:**
- Email matsuk1@proton.me with your use case

#### 3. Enable GitHub Actions

1. Go to your repository's **Actions** tab
2. If prompted, click **I understand my workflows, go ahead and enable them**
3. The bot will start automatically when you push to the `telegram` branch

#### 4. Manual Start (Optional)

You can also manually trigger the bot:
1. Go to **Actions** tab
2. Click on **Telegram Bot** workflow
3. Click **Run workflow** button
4. Select the `telegram` branch
5. Click **Run workflow**

### Monitoring

- View bot logs in the **Actions** tab
- Click on a workflow run to see detailed logs
- The bot will run continuously until you stop it

### Stopping the Bot

1. Go to **Actions** tab
2. Click on the running workflow
3. Click **Cancel workflow** button

## Option 2: Local/Server Deployment

Run the bot on your own machine or server.

### Setup Steps

#### 1. Clone the Repository

```bash
git clone -b telegram https://github.com/YOUR_USERNAME/JiETNG.git
cd JiETNG
```

#### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

#### 3. Configure

Copy the example config and edit it:

```bash
cp config.example.json config.json
nano config.json  # or use your favorite editor
```

Fill in your credentials:
```json
{
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "admin_user_ids": [123456789]
  },
  "api": {
    "base_url": "https://jietng.matsuki.top/api/v1",
    "token": "YOUR_API_TOKEN"
  }
}
```

#### 4. Run the Bot

```bash
python3 bot.py
```

### Keep Bot Running (Linux/macOS)

Use `screen` or `tmux` to keep the bot running after logout:

**Using screen:**
```bash
screen -S telegram-bot
python3 bot.py
# Press Ctrl+A then D to detach
# Later: screen -r telegram-bot to reattach
```

**Using systemd (recommended for servers):**

Create `/etc/systemd/system/telegram-bot.service`:
```ini
[Unit]
Description=JiETNG Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/JiETNG
ExecStart=/usr/bin/python3 /path/to/JiETNG/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## Option 3: Docker Deployment

Run the bot in a Docker container.

### Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "bot.py"]
```

### Build and Run

```bash
# Build image
docker build -t jietng-telegram-bot .

# Run container
docker run -d \
  --name telegram-bot \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN="your_token" \
  -e ADMIN_USER_IDS="123456789" \
  -e API_BASE_URL="https://jietng.matsuki.top/api/v1" \
  -e API_TOKEN="your_api_token" \
  jietng-telegram-bot
```

## Security Best Practices

1. **Never commit `config.json`** - It's already in `.gitignore`
2. **Use environment variables** - Especially for production
3. **Rotate tokens regularly** - Change API tokens periodically
4. **Limit admin access** - Only add trusted user IDs
5. **Monitor logs** - Check for suspicious activity

## Troubleshooting

### Bot doesn't start on GitHub Actions

- Check that all secrets are set correctly
- View workflow logs in Actions tab
- Ensure `telegram` branch has the latest code

### Bot stops after a while

- GitHub Actions has a 6-hour timeout for continuous jobs
- Consider using a dedicated server for 24/7 operation
- Or use a cloud platform with persistent processes

### API connection errors

- Verify `API_BASE_URL` and `API_TOKEN` are correct
- Check network connectivity
- Ensure API server is running

## Cost Comparison

| Platform | Free Tier | 24/7 Uptime | Best For |
|----------|-----------|-------------|----------|
| GitHub Actions | 2000 min/month | ❌ (6h max) | Testing, development |
| Local Server | ✅ Free | ✅ Yes | Personal use |
| VPS (DigitalOcean) | ~$5/month | ✅ Yes | Production |
| Heroku | Limited | ⚠️ Sleeps | Small projects |
| Railway | $5/month | ✅ Yes | Production |

## Recommendations

- **Development/Testing**: GitHub Actions
- **Personal Use**: Local server or Raspberry Pi
- **Production (24/7)**: VPS or cloud platform

## Support

For issues or questions:
- GitHub Issues: https://github.com/Matsuk1/JiETNG/issues
- Email: matsuk1@proton.me

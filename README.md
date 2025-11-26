# JiETNG Telegram Bot

A Telegram Bot that calls JiETNG API to manage maimai accounts.

## Features

### User Commands
- `/start` - Show welcome message and help
- `/bind` - Register new user and get bind URL
- `/unbind` - Delete user account
- `/myinfo` - View personal information
- `/update` - Update user data
- `/b50 [filters]` - Generate Best 50 image (supports filters like `-lv 14 15`)
- `/search <song name>` - Search songs (generates image with covers)
- `/versions` - View all maimai versions

### Admin Commands
- `/users` - View all users
- `/deleteuser <user_id>` - Delete specified user

### Image Generation

This project uses JiETNG's image generation modules:
- Best 50/Best 35/Best 15 score images (detailed card display)
- Search result images (cover grid display)
- Automatic download and caching of icons and covers

## Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configuration

Create `config.json` file:

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

**Configuration:**
- `bot_token`: Get from [@BotFather](https://t.me/BotFather)
- `admin_user_ids`: Admin Telegram User IDs (use [@userinfobot](https://t.me/userinfobot) to get your ID)
- `base_url`: JiETNG API base URL
- `token`: JiETNG API token (request from matsuk1@proton.me)

### 3. Run Bot

```bash
python3 bot.py
```

## Project Structure

```
telegram/
├── bot.py                  # Main bot logic
├── api_client.py           # API client wrapper
├── image_generator.py      # Image generation (b50, search results)
├── modules/                # JiETNG image generation modules
│   ├── config_loader.py    # Config loader
│   ├── image_cache.py      # Image caching and downloading
│   ├── image_manager.py    # Image management utilities
│   ├── record_generator.py # Score image generation
│   └── song_generator.py   # Song card generation
├── assets/                 # Assets
│   ├── fonts/              # Font files
│   ├── pics/               # Images (logo, etc.)
│   └── icon/               # Icon cache directory
├── data/                   # Data directory
│   └── covers/             # Cover cache directory (auto-created)
├── config.json             # Configuration file
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## Usage Examples

### Bind Account
```
/bind
```
Bot will create account and return bind URL. Click the link to complete SEGA account binding.

### View Info
```
/myinfo
```

### View Best 50
```
/b50
```

### Filtered Best 50
```
/b50 -lv 14 15
```
Only show level 14 and 15 songs.

### Search Songs
```
/search freedom
```

### Admin: View All Users
```
/users
```

### Admin: Delete User
```
/deleteuser U123456789
```

## API Usage Example

The bot uses `api_client.py` to call JiETNG API:

```python
from api_client import JiETNGAPIClient

# Initialize client
api_client = JiETNGAPIClient(
    base_url="https://jietng.matsuki.top/api/v1",
    token="YOUR_TOKEN"
)

# Create user
result = api_client.create_user(
    user_id="U123456789",
    nickname="Test User",
    language="en"
)

# Get user info
result = api_client.get_user("U123456789")

# Search songs
result = api_client.search_songs(query="freedom", ver="jp")
```

## Notes

1. **User ID Format**: Telegram Bot automatically converts Telegram User ID to JiETNG format (adds `U` prefix)
2. **Admin Permissions**: Admin user IDs must be configured in `config.json` to use admin commands
3. **API Token**: Ensure you have a valid JiETNG API Token (request from matsuk1@proton.me)
4. **Bind URL Expiration**: Bind URLs expire after 2 minutes

## Development

### API Client (api_client.py)

Wraps all JiETNG API calls:
- User management (create, query, delete, update)
- Records management (get scores)
- Song search
- Version queries

### Bot Logic (bot.py)

Built with `python-telegram-bot`:
- Command handlers
- Permission control
- Error handling
- Interactive replies

## Troubleshooting

### Bot Won't Start
- Check `bot_token` in `config.json`
- Ensure all dependencies are installed: `pip3 install -r requirements.txt`

### API Calls Fail
- Check API `token` in `config.json` is valid
- Check `base_url` is correct
- Review bot logs for error messages

### User Registration Fails
- Ensure API token has access to `/register` endpoint
- Check network connection

## Related Projects

- [JiETNG](https://github.com/Matsuk1/JiETNG) - Main JiETNG LINE Bot project
- [JiETNG Docs](https://jietng.matsuki.work) - Documentation

## License

MIT License

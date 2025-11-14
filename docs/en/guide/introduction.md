# Introduction

JiETNG is a comprehensive 『maimai でらっくす』 score management bot designed to help players track progress, analyze performance, and connect with the community.

## What is JiETNG?

JiETNG (pronounced "jie ting") is a free, feature-rich bot available on LINE that automatically tracks and manages your 『maimai でらっくす』 scores. It fetches your play data directly from the official SEGA website and presents it in beautiful, easy-to-understand visualizations.

## Core Features

### 📊 Score Tracking

- **Best 50**: Generate comprehensive charts of your best scores
- **Real-time Updates**: Sync your latest play records with a single command
- **Historical Data**: Track your progress over time
- **Accurate Calculations**: Rating calculations that conform to official standards

### 🔍 Powerful Search

- **Song Search**: Find any song by name or abbreviation
- **Advanced Filtering**: Filter by level, rating, achievement rate, and more
- **Score Details**: View detailed information for each play

### 👥 Social Features

- **Friend System**: Connect with other players
- **Score Comparison**: Compare scores with friends
- **Friend Requests**: Easy friend adding based on QR codes
- **Leaderboards**: See your ranking among friends

### 📈 Analysis Tools

- **Plate Progress**: Track your progress toward completing plates
- **Level Analysis**: View all scores for specific levels
- **Version Statistics**: See your performance across different versions

## Why Choose JiETNG?

### Casual Players

- **Simple Commands**: Easy-to-use interface for querying scores
- **Visual Charts**: Beautiful graphics make data easy to understand
- **Quick Updates**: Sync your scores in seconds
- **Mobile Friendly**: Works perfectly on your phone

### Competitive Players

- **Detailed Analysis**: In-depth analysis of your performance
- **Rating Tracking**: Monitor your rating changes over time
- **Goal Setting**: Track progress toward specific achievements
- **Friend Competition**: Compare scores with rivals

### Community Organizers

- **Friend Features**: Manage player groups
- **Score Sharing**: Easily share achievements
- **Multi-language**: Support for Japanese, English, and Chinese

## How It Works

```mermaid
graph LR
    A[Player] -->|Send Command| B[JiETNG Bot]
    B -->|Fetch Data| C[SEGA Website]
    C -->|Return Scores| B
    B -->|Generate Chart| D[Score Chart]
    D -->|Send| A
```

1. **You send a command** to JiETNG (e.g., `b50`)
2. **JiETNG fetches** your data from the official SEGA website
3. **Data is processed** and analyzed
4. **Charts are generated** and sent to you

## Platform Support

### LINE

- Large user base in Japan
- Rich UI with FlexMessage
- QuickReply for easy navigation
- Official LINE Bot features
- Multi-language support (Japanese, English, Chinese)

## Security & Privacy

Your data security is paramount:

- ✅ **Encrypted Storage**: All credentials are encrypted
- ✅ **No Third-party Access**: Your data remains private
- ✅ **Transparent**: Open development process
- ✅ **User Control**: Delete your data at any time

[Read our Privacy Policy →](/en/more/privacy)

## Tech Stack

JiETNG is built with modern, reliable technologies:

- **Backend**: Python 3.11+ with Flask
- **Messaging Platform**: python-line-bot-sdk
- **Data Storage**: Encrypted JSON database
- **Image Generation**: Pillow (PIL)
- **Web Scraping**: BeautifulSoup4, lxml

## Open Development

While JiETNG's source code is proprietary, the development process is transparent:

- 📢 Regular updates and announcements
- 🐛 Public issue tracking
- 💡 Feature requests from users
- 📖 Comprehensive documentation

## Community

Join hundreds of 『maimai でらっくす』 players using JiETNG:

- 🌏 Players from Japan, Asia, and around the world
- 💬 Active community discussions
- 🎯 Regular events and competitions
- 🤝 Friendly and welcoming atmosphere

## Getting Started

Ready to start tracking your scores?

[Quick Start Guide →](/en/guide/getting-started)

## Support the Project

JiETNG is free to use and maintained by a single developer. If you find it useful, please consider supporting its development:

[Learn How to Support →](/en/more/support)

---

Have questions? Check out our [FAQ](/en/more/faq) or [contact us](/en/more/support).

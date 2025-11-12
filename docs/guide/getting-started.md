# Getting Started

Welcome to JiETNG! This guide will help you set up the bot and start tracking your Maimai DX scores.

## Prerequisites

Before you begin, make sure you have:

- A LINE account
- A SEGA ID (used to login to the official Maimai DX website)
- Your SEGA ID password

:::warning Security Notice
JiETNG requires your SEGA ID credentials to fetch your scores from the official website. Your credentials are encrypted and stored securely, and are never shared with third parties.
:::

## Step 1: Add the Bot

1. Click this link or scan the QR code: [Add JiETNG on LINE](https://line.me/R/ti/p/@your-bot-id)
2. Click "Add Friend"
3. Start chatting with JiETNG

## Step 2: Bind Your SEGA Account

After adding the bot, you need to link your SEGA ID:

1. Send `bind` to the bot
2. Click the binding link provided
3. Enter your SEGA ID and password
4. Choose your game version (JP or INTL)
5. Click "Bind"

:::tip Language Selection
During binding, you can choose your preferred language (Japanese, English, or Chinese). The bot will remember your preference for all future interactions.
:::

## Step 3: Update Your Scores

After binding, sync your scores from the official website:

```
maimai update
```

or in Japanese:

```
マイマイアップデート
```

This process takes about 20-30 seconds. The bot will:

1. Login to your SEGA account
2. Fetch all your play records
3. Calculate ratings and achievements
4. Store the data securely

:::warning Rate Limiting
To prevent server overload, you can only update your scores once every 5 minutes.
:::

## Step 4: View Your Scores

Now you're ready to use JiETNG! Try these commands:

### Check Your Best 50

```
b50
```

This generates a beautiful chart showing your top 35 old version songs and top 15 current version songs.

### Search for a Song

```
search <song name>
```

Example:
```
search 檄・GEKI
```

### Check a Specific Score

```
<song abbreviation>
```

Example:
```
geki
```

[View all available commands →](/commands/basic)

## What's Next?

Now that you're set up, explore these features:

- 🏆 [Score System](/features/b50) - View your top scores
- 🔍 [Score Search](/features/search) - Find specific songs
- 👥 [Friend System](/features/friends) - Connect with other players

## Troubleshooting

### "SEGA ID not bound" error

Make sure you've completed Step 2 correctly. Try sending `bind` again.

### "Login failed" error

This usually means your SEGA ID or password is incorrect. Double-check your credentials.

### "Maintenance" error

The official Maimai DX website is under maintenance (usually late night JST). Try again later.

### Scores not updating

Make sure you've waited at least 5 minutes since your last update. If the problem persists, try:

```
unbind
bind
maimai update
```

Still having issues? Check our [FAQ](/more/faq) or [contact support](/more/support).

## Privacy & Security

Your data security is our top priority:

- 🔒 Credentials are encrypted using industry-standard encryption
- 🛡️ No third-party access to your data
- 🗑️ You can delete your data anytime with `unbind`
- 📜 Read our full [Privacy Policy](/more/privacy)

---

Ready to dive deeper? Check out our [Feature Guide](/features/b50) or explore [Advanced Commands](/commands/advanced).

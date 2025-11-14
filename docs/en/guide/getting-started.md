# Getting Started

Get started with JiETNG and begin tracking your 『maimai でらっくす』 scores in just three simple steps.

## Prerequisites

Before you begin, make sure you have:

- ✅ LINE account
- ✅ SEGA ID account (for maimai NET)
- ✅ Access to maimai NET
- ✅ Smartphone or computer

## Step 1: Add the Bot

1. Search for **@299bylay** in LINE
2. Or click this link: [@299bylay](https://line.me/R/ti/p/@299bylay)
3. Click "Add Friend"
4. Start a conversation

## Step 2: Bind Your SEGA ID

This is the most important step - connecting your SEGA account to the bot.

### Start Binding

Send this to the bot:

```
bind
```

### Complete the Binding Process

1. The bot will send a button with a **Binding URL**
2. **Click the button** to open the binding webpage
3. **Enter your credentials**:
   - SEGA ID (username)
   - Password
   - Select version (JP or International)
   - Select language
4. **Submit the form**
5. Wait for confirmation message

:::warning ⚠️ Important Security Note
- **Do not enter your password in the chat**
- Only use the official link provided by the bot
- Token expires in 2 minutes
- Your password is stored encrypted
:::

### Verify Binding

Check if binding was successful:

```
get me
```

You should see your SEGA ID, version, and language information.

[Need help with binding? See the detailed binding guide →](/en/guide/binding)

## Step 3: Update Your Scores

Now sync your scores from maimai NET!

### First Sync

```
maimai update
```

### Wait for Processing

- ⏱️ Update time: 20-30 seconds
- 📊 Fetches all your songs and scores

:::tip 🎯 When to Update
- After playing at the arcade
- Before you want to view your latest scores
:::

## Step 4: Generate Your Best 50

Now for the fun part - view your best scores!

### Basic Command

```
b50
```

### What You'll Get

A beautiful chart showing:
- 📊 Your top 35 old songs (songs from previous versions)
- 🎵 Your top 15 new songs (songs from current version)
- 📈 Total rating
- 🎯 Detailed information for each song

### Other Variants

```
b100      # Best 100 (top 70 old + top 30 new)
b35       # Only top 35 old songs
b15       # Only top 15 new songs
```

[Learn more about Best 50 →](/en/commands/record)

## What to Do Next

### Explore Features

Now that you're set up, try these commands:

**Search for songs**:
```
[song name] info
```

**Random song**:
```
random
random 14
```

**Friend list**:
```
friend list
```

**View version achievements**:
```
FESTiVAL achievement
```

### Learn More

- 🎮 [Basic Commands List](/en/commands/basic)
- ❓ [FAQ](/en/more/faq)

## Quick Command Reference

| Command | Purpose |
|----------|---------|
| `maimai update` | Sync scores from maimai NET |
| `b50` | Generate Best 50 chart |
| `[song name] song-info` | Search for song information |
| `[song name] record` | View your score for that song |
| `14 record-list` | View all level 14 scores |
| `friend list` | View your friends |
| `get me` | View account information |
| `unbind` | Unbind SEGA ID |

## Troubleshooting

### "You haven't bound your SEGA ID yet"

**Solution**: Complete Step 2 - use the `bind` command

### "Update failed"

**Possible causes**:
- maimai NET is under maintenance
- Network connection issues
- Incorrect SEGA credentials

**Solutions**:
- Wait a few minutes and try again
- Check if maimai NET is directly accessible
- Use `unbind` then `bind` again

### "Command doesn't work"

**Checklist**:
- ✅ Have you bound your account? (`get me`)
- ✅ Have you updated your scores? (`maimai update`)
- ✅ Is the spelling correct?
- ✅ Are you using the right command?

[View full troubleshooting guide →](/en/more/faq)

## Tips & Tricks

### 💡 Pro Tips

1. **Update regularly**: `maimai update` immediately after playing
2. **Use filters**: `b50 -lv 14 -scr 97 98` to find improvement opportunities
3. **Add friends**: Compare scores with other players
4. **Track plates**: Use `[version] achievement` to track progress
5. **Set goals**: Use `idealb50` to see potential rating

### 🎯 Getting the Most from JiETNG

- 🤝 Join the community Discord
- 📊 Check your progress regularly
- 💬 Share your achievements in the community

## Need Help?

- 📖 [Read full documentation](/en/guide/introduction)
- ❓ [View FAQ](/en/more/faq)
- 💬 [Join Discord](https://discord.gg/NXxFn9T8Xz)
- 🐛 [Report issues](https://github.com/Matsuk1/JiETNG/issues)
- 📧 [Contact support](/en/more/support)

---

**Have fun and improve your rating!** 🎊

# Frequently Asked Questions

Common questions and answers about using JiETNG.

## Getting Started

### What is JiETNG?

JiETNG is a LINE bot for maimai DX players that provides:
- Score tracking and analysis
- Best 50 chart generation
- Song search and discovery
- Plate progress tracking
- Friend ranking comparisons
- And much more!

### Do I need to pay to use JiETNG?

No! JiETNG is completely **free to use**. However, you can support development through [donations](/en/more/support).


### Do I need a SEGA ID?

Yes, to use most features you need:
- A SEGA ID account
- Access to maimai NET (online score tracking)
- Binding your account to the bot

See [Account Binding](/en/guide/binding) for setup instructions.

## Account Binding

### How do I bind my SEGA ID?

1. Send `bind` to the bot
2. Click the binding URL button
3. Enter your SEGA ID and password on the web form
4. Select your server version
5. Confirm binding

**Important**: Do NOT type your credentials in the chat. Binding is web-based only.

See [Account Binding Guide](/en/guide/binding) for details.

### Can I type my SEGA credentials in the chat?

**No.** For security reasons, JiETNG uses web-based binding only. Never type your password in the chat.

### The binding link expired. What do I do?

Binding tokens expire after **2 minutes**. Simply send `bind` again to get a new link.

## Using Features

### How do I generate my Best 50?

Send one of these commands:
- `b50`
- `best50`
- `ベスト50`

Make sure you've bound your SEGA ID first!

See [Score Commands](/en/commands/record) for details.

### How often should I update my scores?

Update after each play session:
```
maimai update
```

This fetches your latest scores from maimai NET.

### How long does score update take?

Usually 20 to 30 seconds, depending on:
- Number of songs you've played
- SEGA server response time
- Queue wait time (if many users are updating)

### Why isn't my latest score showing?

1. **Did you update?** Run `maimai update` first
2. **Check maimai NET**: Is your score on the official site?
3. **Wait time**: Scores may take a few minutes to appear on maimai NET
4. **Network issues**: SEGA servers may be slow

## Features and Commands

### What is the friend system?

Add other JiETNG users as friends to:
- Compare Best 50 charts
- View each other's scores
- Build your maimai community

See [Friend System](/en/features/friends) for details.

## Troubleshooting

### "You haven't bound your SEGA ID yet"

**Solution**: Bind your account with `bind` command.

See [Account Binding](/en/guide/binding).

### "Failed to update scores"

**Possible causes:**
- SEGA servers are down
- Wrong SEGA credentials
- Network timeout
- maimai NET maintenance

**Solutions:**
- Wait a few minutes and try again
- Verify credentials by logging into maimai NET directly
- Check SEGA announcements for maintenance
- Re-bind if credentials changed

### "Song not found"

**Causes:**
- Song name typo
- Song doesn't exist in maimai DX
- Wrong version (jp vs intl)

**Solutions:**
- Try different keywords
- Check spelling
- Search on [maimai wiki](https://maimai.fandom.com/)
- Try Japanese name instead of English (or vice versa)

### Commands not working

**Troubleshooting steps:**
1. Check spelling and syntax
2. Verify you're bound (`get me`)
3. Update scores (`maimai update`)
4. Check [Command Reference](/en/commands/basic)
5. Try simpler command first (e.g., `b50` before `b50 -lv 14`)


## Community and Support

### How can I report a bug?

1. Check [FAQ](/en/more/faq) (this page)
2. Search [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
3. If not found, create new issue with:
   - Description of bug
   - Steps to reproduce
   - Screenshots (if applicable)
   - Your version (JP/International)

### How can I support the project?

- 💰 **Financial Support**: [Donate](/en/more/support)
- ⭐ **GitHub**: Star the [repository](https://github.com/Matsuk1/JiETNG)
- 📢 **Share**: Tell friends about JiETNG
- 📝 **Contribute**: Improve documentation, fix bugs, add features
- 🐛 **Report**: Help identify and report bugs

See [Support Page](/en/more/support) for details.

## Privacy and Security

### Is my data safe?

Yes! JiETNG:
- ✅ Encrypts your SEGA credentials
- ✅ Only accesses public maimai NET data
- ✅ Does not store chat history
- ✅ Follows data protection best practices

See [Privacy Policy](/en/more/privacy) for details.

### How do I delete my data?

Send `unbind` to permanently delete all your data from JiETNG.

## Still Have Questions?

### Documentation

- 📖 [Getting Started](/en/guide/getting-started)
- 📚 [Command Reference](/en/commands/basic)
- 🔍 [Score Commands](/en/commands/record)

### Community

- 💬 [Discord Server](https://discord.gg/NXxFn9T8Xz)
- 🐛 [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
- 📧 [Support Page](/en/more/support)

---

**Can't find your answer?**

1. Search this FAQ (Ctrl+F / Cmd+F)
2. Check other [documentation pages](/en/)
3. Search [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
4. Ask in [Discord](https://discord.gg/NXxFn9T8Xz)
5. Create new [GitHub Issue](https://github.com/Matsuk1/JiETNG/issues/new)

We're here to help! 💙

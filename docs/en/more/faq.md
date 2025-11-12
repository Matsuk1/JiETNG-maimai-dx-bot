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

No! JiETNG is completely **free to use**. However, you can support development through [donations](/more/support).

### Which platforms does JiETNG support?

Choose the platform you prefer - all features work on both!

### Do I need a SEGA ID?

Yes, to use most features you need:
- A SEGA ID account
- Access to maimai NET (online score tracking)
- Binding your account to the bot

See [Account Binding](/guide/binding) for setup instructions.

## Account Binding

### How do I bind my SEGA ID?

1. Send `bind` to the bot
2. Click the binding URL button
3. Enter your SEGA ID and password on the web form
4. Select your version (JP or International)
5. Confirm binding

**Important**: You DO NOT type your credentials in the chat. Binding is web-based only.

See [Account Binding Guide](/guide/binding) for details.

### Can I type my SEGA credentials in the chat?

**No.** For security reasons, JiETNG uses web-based binding only. Never type your password in the chat.

### The binding link expired. What do I do?

Binding tokens expire after **2 minutes**. Simply send `bind` again to get a new link.

### Can I bind multiple SEGA IDs?

No. One LINE account can only bind one SEGA ID at a time. To rebind:
1. Send `unbind`
2. Send `bind` again with new credentials

### I forgot which SEGA ID I bound. How do I check?

Send `get me` or `getme` to see your current binding information.

### How do I unbind my account?

Send `unbind` to remove your SEGA ID from the bot. This will delete all your stored data.

:::warning
Unbinding is permanent! Your scores, friend list, and settings will be deleted.
:::

## Using Features

### How do I generate my Best 50?

Send one of these commands:
- `b50`
- `best50`
- `ベスト50`

Make sure you've bound your SEGA ID first!

See [Best 50 Feature](/features/b50) for details.

### How often should I update my scores?

Update after each play session:
```
maimai update
```

This fetches your latest scores from maimai NET.

### How long does score update take?

Usually 30 seconds to 2 minutes, depending on:
- Number of songs you've played
- SEGA server response time
- Queue wait time (if many users are updating)

### Why isn't my latest score showing?

1. **Did you update?** Run `maimai update` first
2. **Check maimai NET**: Is your score on the official site?
3. **Wait time**: Scores may take a few minutes to appear on maimai NET
4. **Network issues**: SEGA servers may be slow

### Can I search for songs?

Yes! Use:
```
[song name] info
```

Example: `blew moon info`

See [Song Search](/features/search) for details.

### How do I check a specific song's record?

```
[song name] record
```

Example: `オンゲキ音頭 のレコード`

## Features & Commands

### What is the friend system?

Add other JiETNG users as friends to:
- Compare Best 50 charts
- View each other's scores
- Build your maimai community

See [Friend System](/features/friends) for details.

### Can I compare scores with non-JiETNG users?

No. Friend features only work between users who both:
- Use JiETNG
- Have bound their SEGA IDs
- Have added each other as friends

### What are the advanced filters?

Use `-lv`, `-ra`, `-dx`, `-scr` to filter songs:
```
b50 -lv 14 -scr 97 98
```

See [Advanced Filters](/commands/advanced) for complete guide.

## Technical Questions

### Is my data safe?

Yes! JiETNG:
- ✅ Encrypts your SEGA credentials
- ✅ Only accesses public maimai NET data
- ✅ Does not store chat history
- ✅ Follows data protection best practices

See [Privacy Policy](/more/privacy) for details.

### Where is my data stored?

Your data is stored on the bot's server, including:
- SEGA ID and credentials (encrypted)
- Score records
- Personal settings
- Friend list

Data is deleted when you `unbind`.

### Can I export my data?

Currently, you can:
- Take screenshots of charts
- Copy text from commands like `get me`
- Request data removal via `unbind`

Automated export features may be added in the future.

### Does JiETNG work offline?

No. JiETNG requires:
- Internet connection
- Access to SEGA servers (for updates)
- LINE connection

### Why is the bot slow sometimes?

Possible reasons:
- **High server load**: Many users updating simultaneously
- **SEGA server issues**: maimai NET may be slow
- **Network problems**: Your internet connection
- **Queue wait**: Requests are processed in order

Image generation and score updates are queued to prevent overload.

## Troubleshooting

### "You haven't bound your SEGA ID yet"

**Solution**: Bind your account with `bind` command.

See [Account Binding](/guide/binding).

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
4. Check [Command Reference](/commands/basic)
5. Try simpler command first (e.g., `b50` before `b50 -lv 14`)

### Bot not responding

**Possible causes:**
- Bot is down (rare)
- Your message was too long
- Network issues
- Chat platform issues (LINE)

**Solutions:**
- Wait 1-2 minutes and try again
- Restart your LINE app
- Check bot status (if status page exists)
- Report on [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

## Performance & Optimization

### How can I make B50 generation faster?

B50 generation is already optimized, but you can:
- Update scores regularly (keeps data fresh)
- Use simpler commands when possible
- Avoid peak hours (if server is slow)

### Why does maimai update take so long?

Factors affecting update time:
- **Number of songs**: More songs = longer time
- **SEGA server speed**: Out of bot's control
- **Queue position**: Other users updating before you
- **Network**: Your/server's internet speed

Typical times: 30 seconds to 2 minutes for full update.

### Can I reduce image generation time?

Image generation is already optimized. Some tips:
- Simpler charts (b50) are faster than complex ones
- Server load varies (try off-peak hours)
- Use cached data when possible (images may be cached)

## JP vs International

### What's the difference?

| Aspect | Japan (jp) | International (intl) |
|--------|-----------|---------------------|
| **Machines** | Japan only | Outside Japan |
| **Song updates** | First | Delayed |
| **Events** | Japan-specific | Region-specific |
| **maimai NET** | maimaidx.jp | maimaidx-eng.com |

### Can I switch between JP and International?

You need to `unbind` and `bind` again with the new version selected.

:::warning
Switching versions deletes your current data! Make sure you want to switch.
:::

### Can I have both JP and International accounts?

No. One LINE account can only bind one SEGA ID of one version at a time.

## Contributing & Support

### How can I report a bug?

1. Check [FAQ](/more/faq) (this page)
2. Search [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
3. If not found, create new issue with:
   - Description of bug
   - Steps to reproduce
   - Screenshots (if applicable)
   - Your version (JP/International)

### How can I request a feature?

Submit on [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues) with:
- Feature description
- Use case / benefit
- Examples (if applicable)

### Can I contribute code?

Yes! JiETNG is open source. See [GitHub](https://github.com/Matsuk1/JiETNG) for:
- Contribution guidelines
- Development setup
- Code standards
- Pull request process

### How can I support the project?

- 💰 **Financial**: [Donate](/more/support)
- ⭐ **GitHub**: Star the [repository](https://github.com/Matsuk1/JiETNG)
- 📢 **Share**: Tell friends about JiETNG
- 📝 **Contribute**: Improve documentation, fix bugs, add features
- 🐛 **Report**: Help identify and report bugs
- 🌐 **Translate**: Help with translations

See [Support Page](/more/support) for details.

## Language & Localization

### What languages does JiETNG support?

Currently:
- 🇯🇵 **Japanese** (日本語)
- 🇬🇧 **English**
- 🇨🇳 **Chinese** (中文) - partial

Commands work in multiple languages (e.g., `b50`, `ベスト50`, `best50` all work).

### How do I change my language?

Language is automatically detected from your maimai NET settings when you bind.

To change:
1. Update language on maimai NET
2. `unbind` from JiETNG
3. `bind` again (new language will be detected)

Or specify during binding if the web form allows.

### Can I help translate?

Yes! We welcome translation contributions:
- Documentation pages
- Bot messages
- Error messages
- Help text

Contact via [GitHub](https://github.com/Matsuk1/JiETNG) or [Support](/more/support).

## Advanced Usage

### What are the rate limits?

JiETNG has rate limiting to prevent abuse:
- Image generation: Limited per user per minute
- Score updates: Queue-based (one at a time per user)
- Search: Fast, minimal limits

If you hit a rate limit, wait a few seconds and try again.

### Can I use JiETNG with automation tools?

**No.** Using automation tools (bots, scripts) to spam commands may result in:
- Rate limiting
- Temporary ban
- Permanent ban (for severe abuse)

Use JiETNG responsibly and manually.

### Are there any hidden commands?

Admin commands exist but require admin privileges. Regular users have access to all documented commands.

See [Command Reference](/commands/basic) for complete list.

### Can I run my own instance of JiETNG?

Yes! JiETNG is open source. See [GitHub](https://github.com/Matsuk1/JiETNG) for:
- Installation guide
- Configuration instructions
- Server requirements
- Self-hosting tips

## Privacy & Security

### What data does JiETNG collect?

JiETNG stores:
- ✅ SEGA ID and credentials (encrypted)
- ✅ Score records (from maimai NET)
- ✅ Friend list
- ✅ Settings (language, version)
- ❌ Chat messages (NOT stored)
- ❌ Personal info beyond maimai NET data

### Who can see my data?

- **You**: Full access via commands
- **Friends**: Only what you share (friend B50, etc.)
- **Bot admin**: For debugging/support only
- **Public**: Nothing (private by default)

### How do I delete my data?

Send `unbind` to permanently delete all your data from JiETNG.

### Is my SEGA password visible to admins?

No. Passwords are:
- Encrypted before storage
- Never logged in plain text
- Only used for maimai NET API calls
- Not accessible even to admins

## Still Have Questions?

### Documentation

- 📖 [Getting Started](/guide/getting-started)
- 📚 [Command Reference](/commands/basic)
- 🔍 [Feature Guides](/features/b50)
- 💡 [Advanced Usage](/commands/advanced)

### Community

- 💬 [Discord Server](https://discord.gg/your-invite-link)
- 🐛 [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
- 📧 [Support Page](/more/support)

### Quick Help

Try these commands in the bot:
- `help` - Basic help message
- `get me` - Your account info
- `friend list` - Your friends

---

**Can't find your answer?**

1. Search this FAQ (Ctrl+F / Cmd+F)
2. Check other [documentation pages](/)
3. Search [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)
4. Ask in [Discord](https://discord.gg/your-invite-link)
5. Create new [GitHub Issue](https://github.com/Matsuk1/JiETNG/issues/new)

We're here to help! 💙

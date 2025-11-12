# Account Binding

Learn how to bind your SEGA ID to JiETNG to access your maimai DX scores and records.

## How Binding Works

JiETNG uses **web-based binding** with secure time-limited tokens. Your credentials are submitted through a secure web form, not in the chat.

:::warning Important
There is NO command-line binding. You cannot type your credentials directly in the chat. All binding is done through a secure web interface.
:::

## Binding Your Account

### Step 1: Start Binding Process

Send one of these commands to the bot:

- `bind`
- `segaid bind`
- `バインド` (Japanese)

### Step 2: Open the Binding URL

The bot will send you a button with a unique URL:

```
SEGA アカウント連携
SEGA アカウントと連携されます
有効期限は発行から2分間です

[押しで連携] ← Click this button
```

:::tip Token Expiration
The binding token expires after **2 minutes**. If it expires, simply send the `bind` command again to get a new token.
:::

### Step 3: Enter Your Credentials

The web form will ask for:

- **SEGA ID**: Your SEGA account username
- **Password**: Your SEGA account password
- **Version**: Select `jp` (Japan) or `intl` (International)
- **Language**: Select your preferred language

:::danger Security Note
- Never share your SEGA credentials with anyone
- The bot does not store your password in plain text
- Only use the official binding URL provided by the bot
:::

### Step 4: Confirmation

Once binding is successful, you'll receive a confirmation message and can start using all features.

## Checking Binding Status

To verify your account is bound:

```
get me
```

or

```
getme
ゲットミー
```

This will display your current binding information including:
- SEGA ID
- Version (jp/intl)
- Language setting
- Personal info status

## Unbinding Your Account

To remove your SEGA ID from the bot:

```
unbind
```

or

```
アンバインド
```

:::warning Data Removal
Unbinding will **permanently delete** all your stored data including:
- SEGA credentials
- Score records
- Friend list
- Personal information
- Language preferences

This action cannot be undone.
:::

## Troubleshooting

### Token Expired Error

**Problem**: The binding URL shows "Token expired" or "Invalid token"

**Solution**:
- Send `bind` again to generate a new token
- Complete the binding within 2 minutes
- Make sure you're using the latest URL

### Invalid Credentials

**Problem**: "Login failed" or "Invalid SEGA ID/Password"

**Solution**:
- Double-check your SEGA ID and password
- Make sure you're using the correct version (jp vs intl)
- Try logging in to [maimai NET](https://maimaidx.jp/maimai-mobile/) directly to verify credentials
- For International version, use [maimai NET DX International](https://maimaidx-eng.com/maimai-mobile/)

### Already Bound Error

**Problem**: "This SEGA ID is already bound to another account"

**Solution**:
- Each SEGA ID can only be bound to one LINE account at a time
- If you need to rebind, first `unbind` from the previous account
- Contact support if you've lost access to the previous account

### Web Form Not Loading

**Problem**: The binding URL doesn't open or shows an error

**Solution**:
- Check your internet connection
- Try opening the URL in a different browser
- Clear your browser cache and cookies
- If the issue persists, report it on [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

## Version Selection

### Japan (jp)

Use if you play on Japanese arcade machines:
- Official maimai DX in Japan
- Standard (スタンダード) and DX charts
- All Japanese exclusive songs
- URL: https://maimaidx.jp/maimai-mobile/

### International (intl)

Use if you play outside Japan:
- maimai DX machines in other countries
- May have delayed song updates compared to JP
- Different regional events
- URL: https://maimaidx-eng.com/maimai-mobile/

:::tip Choosing the Right Version
Select the version that matches where you physically play maimai DX. Your account version cannot be changed without unbinding and rebinding.
:::

## Security Best Practices

### Protect Your Account

1. **Never share binding URLs**: Each token is unique to you and expires in 2 minutes
2. **Use strong passwords**: For your SEGA account
3. **Verify the domain**: Make sure the binding URL is from the official JiETNG domain
4. **Log out after use**: On shared devices
5. **Report suspicious activity**: If you notice unauthorized access

### Privacy

- Your SEGA credentials are encrypted
- The bot only accesses public game data from maimai NET
- No private messages or chat history are stored
- See [Privacy Policy](/more/privacy) for details

## What Happens After Binding?

Once bound, you can:

✅ Generate Best 50 charts
✅ Check song records
✅ Track plate progress
✅ Search songs
✅ Update scores from maimai NET
✅ Add friends and view friend rankings
✅ Generate your maimai pass card
✅ Find nearby stores

## Automatic Score Updates

After binding, you can manually update your scores:

```
maimai update
```

or

```
update
アップデート
```

This fetches your latest scores from maimai NET and updates your records in the bot.

:::tip Update Frequency
Score updates are queued and processed sequentially to avoid overloading the SEGA servers. During peak times, your update may take a few minutes to complete.
:::

## Multiple Devices

- Your binding is tied to your LINE account, not your device
- You can use the bot on any device where you're logged in
- Switching devices doesn't require rebinding
- If you change your LINE account, you need to bind again

## Need Help?

- Check the [FAQ](/more/faq) for common questions
- Report issues on [GitHub](https://github.com/Matsuk1/JiETNG/issues)
- Contact support via the [Support page](/more/support)

---

**Next Steps:**
- [Getting Started Guide](/guide/getting-started) - Basic usage
- [Command Reference](/commands/basic) - Available commands
- [Best 50 Feature](/features/b50) - Generate ranking charts

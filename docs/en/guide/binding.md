# Account Binding

Learn how to bind your SEGA ID to JiETNG to access your 『maimai でらっくす』 scores and records.

## Binding Mechanism

JiETNG uses a **web-based binding** approach with secure time-limited tokens. Your credentials are submitted through a secure web form rather than being entered in the chat.

:::warning Important
There is no command-line binding method. You cannot enter your credentials directly in the chat. All binding is done through a secure web interface.
:::

## Binding Your Account

### Step 1: Start the Binding Process

Send one of these commands to the bot:

- `bind`
- `segaid bind`
- `バインド` (Japanese)

### Step 2: Open the Binding URL

The bot will send a button with a unique URL:

```
SEGA アカウント連携
SEGA アカウントと連携されます
有効期限は発行から2分間です

[押しで連携] ← Click this button
```

:::tip Token Expiration
Binding tokens expire after **2 minutes**. If it expires, simply send the `bind` command again to get a new token.
:::

### Step 3: Enter Your Credentials

The web form will ask you for:

- **Language**: Select your preferred language
- **SEGA ID**: Your SEGA account username
- **Password**: Your SEGA account password
- **Version**: Choose `jp` (Japan) or `intl` (International)

:::danger Security Tips
- Never share your SEGA credentials with anyone
- The bot does not store your password in plain text
- Only use the official binding URL provided by the bot
:::

### Step 4: Confirmation

After successful binding, you'll receive a confirmation message and can start using all features.

## Checking Binding Status

Verify if your account is bound:

```
get me
getme
ゲットミー
```

This will show your current binding information, including:
- SEGA ID
- Version (jp/intl)
- Language settings
- Personal information status

## Unbinding

Remove your SEGA ID from the bot:

```
unbind
```

:::warning Data Deletion
Unbinding will **permanently delete** all your stored data, including:
- SEGA credentials
- Score records
- Friend lists
- Personal information
- Language preferences

This action cannot be undone.
:::

## Troubleshooting

### Token Expired Error

**Problem**: Binding URL shows "Token expired" or "Invalid token"

**Solution**:
- Send `bind` again to generate a new token
- Complete binding within 2 minutes
- Make sure you're using the latest URL

### Invalid Credentials

**Problem**: "Login failed" or "Invalid SEGA ID/Password"

**Solution**:
- Double-check your SEGA ID and password
- Make sure you're using the correct version (jp vs intl)
- Try logging into [maimai NET](https://maimaidx.jp/maimai-mobile/) directly to verify credentials
- For international version, use [maimai NET DX International](https://maimaidx-eng.com/maimai-mobile/)

### Already Bound Error

**Problem**: "This SEGA ID is already bound to another account"

**Solution**:
- Each SEGA ID can only be bound to one LINE account at a time
- To rebind, first `unbind` from the previous account
- If you can't access the previous account, contact support

### Web Form Won't Load

**Problem**: Binding URL won't open or shows errors

**Solution**:
- Check your internet connection
- Try opening in a different browser
- Clear browser cache and cookies
- If the problem persists, report it on [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

## Version Selection

### Japan (jp)

If you play at arcades in Japan:
- Official Japanese 『maimai でらっくす』
- Standard and DX charts
- All Japan-exclusive songs
- URL: https://maimaidx.jp/maimai-mobile/

### International (intl)

If you play outside Japan:
- 『maimai でらっくす』 machines in other countries
- Song updates may lag behind JP version
- Different regional events
- URL: https://maimaidx-eng.com/maimai-mobile/

:::tip Choose the Right Version
Select the version that matches where you actually play 『maimai でらっくす』. You cannot change the account version without unbinding and rebinding.
:::

## Security Best Practices

### Protecting Your Account

1. **Don't share binding URLs**: Each token is unique to you and expires in 2 minutes
2. **Use strong passwords**: Set a strong password for your SEGA account
3. **Verify the domain**: Make sure the binding URL comes from the official JiETNG domain
4. **Log out after use**: Remember to log out when using shared devices
5. **Report suspicious activity**: Report any unauthorized access

## Features Available After Binding

Once bound, you can:

✅ Generate Best 50 charts
✅ View song records
✅ Track plate progress
✅ Search for songs
✅ Update scores from maimai NET
✅ Add friends and view friend rankings
✅ Generate your maimai pass card
✅ Find nearby shops

## Automatic Score Updates

After binding, you can manually update scores:

```
maimai update
update
アップデート
```

This will fetch your latest scores from maimai NET and update the records in the bot.

:::tip Update Frequency
Score updates are queued and processed sequentially to avoid overloading SEGA servers. During peak times, your update may take a few minutes to complete.
:::

## Multi-device Usage

- Binding is associated with your LINE account, not the device
- You can use the bot on any device where you're logged in
- No need to rebind when switching devices
- If you change LINE accounts, you'll need to rebind

## Need Help?

- Check the [FAQ](/en/more/faq) for common questions
- Report issues on [GitHub](https://github.com/Matsuk1/JiETNG/issues)
- Contact support via the [support page](/en/more/support)

---

**Next Steps:**
- [Getting Started Guide](/en/guide/getting-started) - Basic usage
- [Command Reference](/en/commands/basic) - Available commands

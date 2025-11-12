# Basic Commands

This page covers all the essential commands you'll use frequently when working with JiETNG.

## Account Management

### Bind SEGA Account

Link your SEGA ID to start using JiETNG:

```
bind
```

This will provide a web link for secure binding.

### Unbind Account

Remove your SEGA ID and delete all stored data:

```
unbind
```

:::danger Warning
This action is irreversible. All your data will be permanently deleted.
:::

### Update Scores

Fetch your latest scores from SEGA:

```
maimai update
update
マイマイアップデート
レコードアップデート
```

## Calculator

### Achievement Rate Calculator

Calculate the percentage needed to reach target achievement rates:

```
calc <tap> <hold> <slide> [<touch>] <break>
```

Example (for a song with 100 taps, 50 holds, 30 slides, 20 touches, 10 breaks):
```
calc 100 50 30 20 10
```

Displays achievement rate values for each note type.

## User Profile

### View Maipass

Generate a player card with QR code:

```
maipass
pass
```

This creates a shareable card containing:
- Your username and rating
- QR code for adding friends
- Profile icon and plate

### Get User Information

```
getme
```

## Help & Information

### View Help

```
help
ヘルプ
```

Displays quick command reference.

## Tips

### Command Shortcuts

Many commands have multiple aliases:

```
b50 = best50
b100 = best100
```

### Case Insensitive

Commands are case-insensitive:

```
B50 = b50 = Best50
RANDOM = random
```

### Spacing

Most commands handle extra spaces gracefully:

```
search  geki     # Works fine
b50              # No space needed
```

## Next Steps

- 📖 [Score Commands](/en/commands/record) - Score viewing commands

---

Need help? Check the [FAQ](/en/more/faq) or [contact support](/en/more/support).

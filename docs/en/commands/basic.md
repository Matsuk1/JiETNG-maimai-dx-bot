# Basic Commands

This page covers all the essential commands you'll use regularly with JiETNG.

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

**Rate limit**: Once every 5 minutes

## Viewing Scores

### Best Charts

Generate your Best 50 or Best 100:

```
b50                # Best 50 (35 standard + 15 DX)
b100               # Best 100 (70 standard + 30 DX)
best50             # Same as b50
best100            # Same as b100
```

### Best Variations

```
best35             # Top 35 standard songs only
best15             # Top 15 DX songs only
ab50               # All Best 50 (ignore type)
ab35               # All Best 35
apb50              # All Perfect Best 50 (AP/AP+ only)
idlb50             # Ideal Best 50 (simulated SSS+)
```

### Recent Plays

View your 50 most recent plays:

```
recent
rct50
```

## Song Search

### Search by Name

Find songs by title:

```
search <song name>
```

Examples:
```
search 檄
search geki
search shama
```

**Supported**:
- Full song name (Japanese, English, Chinese)
- Partial names
- Romaji
- Common abbreviations

### Search by Song ID

Use the official song ID:

```
id:<song_id>
```

Example:
```
id:11051
```

## Song Information

### View Song Details

Get comprehensive info about a song:

```
<song abbreviation>
```

Examples:
```
geki              # Show 檄・GEKI・GEKI info
ifuudoudou        # Show イフウドウドウ info
```

### View Your Score

If you've played the song, it shows your score. If not, it shows song information.

## Level-Based Queries

### View All Scores for a Level

```
lv<level>
lv<level> <page>
```

Examples:
```
lv15              # All your level 15 scores (page 1)
lv14+ 2           # Level 14.7+ scores (page 2)
lv13              # Level 13.0-13.6 scores
```

**Level formats**:
- `15` = 15.0
- `15+` = 15.7+
- `14` = 14.0-14.6
- `14+` = 14.7-14.9

### Pagination

Each page shows up to 50 scores. Use page numbers for more:

```
lv15 1            # Page 1
lv15 2            # Page 2
lv15 3            # Page 3
```

## Plate Progress

Track your progress toward plate completions:

```
<version><plate_type>
```

Examples:
```
真極              # BUDDiES 極 plate
真将              # BUDDiES 将 plate
真神              # BUDDiES 神 plate
真舞舞            # BUDDiES 舞舞 plate (Sync plate)
```

**Version abbreviations**:
- `真` = BUDDiES
- `祭` = FESTiVAL+
- `宴` = FESTiVAL
- `舞` = UNiVERSE+
- `双` = UNiVERSE

**Plate types**:
- `極` = FC+ or better on all Master charts
- `将` = SSS or better on all Master charts
- `神` = AP or better on all Master charts
- `舞舞` = FDX or better on all Master charts

## Random Song

Get a random song recommendation:

```
random
ランダム曲
```

**With filters**:
```
random <level>            # Random from specific level
random lv14+              # Random level 14.7+ song
```

## Calculator

### Achievement Calculator

Calculate what % you need for target achievement:

```
calc <tap> <hold> <slide> <touch> <break>
```

Example (song with 100 tap, 50 hold, 30 slide, 20 touch, 10 break):
```
calc 100 50 30 20 10
```

Shows the achievement value for each note type.

## User Profile

### View Maipass

Generate your player card with QR code:

```
maipass
pass
```

This creates a shareable card with:
- Your username and rating
- QR code for friend adding
- Profile icon and plate

### Get User Info

```
me
profile
```

Shows your current:
- Rating
- Dan/Class
- Last update time
- Bind status

## Help & Info

### View Help

```
help
ヘルプ
```

Displays quick command reference.

### View Bot Info

```
about
info
```

Shows bot version, uptime, and statistics.

## Language

### Change Language

```
lang ja           # 日本語
lang en           # English
lang zh           # 中文
```

All future messages will be in your selected language.

## Tips

### Command Shortcuts

Many commands have multiple aliases:

```
b50 = best50
b100 = best100
lv = level
```

### Case Insensitive

Commands are not case-sensitive:

```
B50 = b50 = Best50
RANDOM = random
```

### Spaces

Most commands handle extra spaces gracefully:

```
search  geki     # Works fine
b50              # No space needed
lv 15            # Space optional
```

## Next Steps

- 📖 [Record Commands](/commands/record) - Commands for Record viewing
- ❓ [FAQ](/more/faq) - Common questions

---

Need help? Check the [FAQ](/more/faq) or [contact support](/more/support).

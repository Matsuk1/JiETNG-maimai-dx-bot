# JiETNG Complete Command List

This document lists all available commands for the JiETNG Maimai DX LINE Bot.

[简体中文](COMMANDS.md) | English | [日本語](COMMANDS_JP.md)

---

## Table of Contents

- [Basic Commands](#basic-commands)
- [Account Management](#account-management)
- [Score Queries](#score-queries)
- [Song Queries](#song-queries)
- [Version Achievements](#version-achievements)
- [Friend Features](#friend-features)
- [Utility Commands](#utility-commands)
- [Admin Commands](#admin-commands)

---

## Basic Commands

### System Check

| Command | Aliases | Description |
|---------|---------|-------------|
| `check` | `チェック` | Check if Bot is online |
| `network` | `ネットワーク` | Check network connection status |

---

## Account Management

### Binding and Viewing

| Command | Aliases | Description |
|---------|---------|-------------|
| `segaid bind` | `sega bind`, `bind`, `segaid バインド`, `sega バインド`, `バインド` | Bind SEGA account |
| `get me` | `getme`, `ゲットミー` | View current account binding info |
| `unbind` | `アンバインド` | Unbind account |

### Data Update

| Command | Aliases | Description |
|---------|---------|-------------|
| `maimai update` | `update`, `record update`, `マイマイアップデート`, `レコードアップデート`, `アップデート` | Sync latest scores from maimai NET |

**Notes**:
- Data update requires SEGA account binding
- Update process may take 1-2 minutes
- Rate limit: Maximum 2 requests per 30 seconds

---

## Score Queries

### Standard Score Charts

| Command | Aliases | Description |
|---------|---------|-------------|
| `b50` | `best50`, `best 50`, `ベスト50` | Best 35 (old ver.) + Best 15 (new ver.) |
| `b100` | `best100`, `best 100`, `ベスト100` | Best 70 (old ver.) + Best 30 (new ver.) |
| `b35` | `best35`, `best 35`, `ベスト35` | Old version Best 35 only |
| `b15` | `best15`, `best 15`, `ベスト15` | New version Best 15 only |

### Special Score Charts

| Command | Aliases | Description |
|---------|---------|-------------|
| `ab50` | `allb50`, `all best 50`, `オールベスト50` | Mixed version Best 50 |
| `ab35` | `allb35`, `all best 35`, `オールベスト35` | Mixed version Best 35 |
| `ap50` | `apb50`, `all perfect 50`, `オールパーフェクト50` | AP/APP only Best 50 |
| `rct50` | `r50`, `recent50`, `recent 50` | Recent 50 plays |
| `idealb50` | `idlb50`, `ideal best 50`, `理想的ベスト50` | Ideal Best 50 (auto-upgrade to next rank) |
| `unknown` | `unknown songs`, `unknown data`, `未発見` | Unrecognized songs |

### Advanced Filters

All score chart commands support the following filters:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-lv [min] [max]` | Filter by chart constant (max optional, unlimited if omitted) | `b50 -lv 13.2 13.8` or `b50 -lv 13.2` |
| `-ra [min] [max]` | Filter by Rating (max optional, unlimited if omitted) | `b50 -ra 301 312` or `b50 -ra 301` |
| `-scr [min] [max]` | Filter by achievement (max optional, unlimited if omitted) | `b50 -scr 100.3 100.8` or `b50 -scr 100.3` |
| `-dx [min] [max]` | Filter by DX score percentage (max optional, unlimited if omitted) | `b50 -dx 92 95` or `b50 -dx 92` |

**Note**: All filter parameters support single-parameter mode (minimum only, no upper limit):
- `-lv 13.2` means chart constant ≥13.2 (no upper limit)
- `-ra 301` means Rating ≥301 (no upper limit)
- `-scr 100.3` means achievement ≥100.3% (no upper limit)
- `-dx 92` means DX score ≥92% (no upper limit)

#### Filter Examples

```
b50 -lv 13.2 13.8                    # B50 with constant 13.2-13.8
b50 -lv 13.2                         # B50 with constant ≥13.2 (no limit)
b50 -ra 301 312                      # B50 with Rating 301-312
b50 -ra 301                          # B50 with Rating ≥301 (no limit)
b50 -scr 100.3 100.8                 # B50 with achievement 100.3%-100.8%
b50 -scr 100.3                       # B50 with achievement ≥100.3% (no limit)
b50 -dx 92 95                        # B50 with DX score 92%-95%
b50 -dx 92                           # B50 with DX score ≥92% (no limit)
b50 -lv 13.2 13.8 -scr 100.0         # B50 with constant 13.2-13.8 and achievement ≥100%
b100 -lv 13.0 14.9 -dx 92 95         # B100 with constant 13.0-14.9 and DX 92%-95%
idealb50 -lv 13.5 14.0               # Ideal B50 with constant 13.5-14.0
```

### Yang Rating (Past Version Rating)

| Command | Aliases | Description |
|---------|---------|-------------|
| `yang` | `yrating`, `yra`, `ヤンレーティング` | Generate Yang Rating chart (by version) |

---

## Song Queries

### Song Information

| Command Format | Aliases | Description | Example |
|----------------|---------|-------------|---------|
| `[Song]ってどんな曲` | `[Song]info`, `[Song]song-info` | Search song details | `ヒバナってどんな曲` |
| `[Song]のレコード` | `[Song]record`, `[Song]song-record` | View personal score | `ヒバナのレコード` |

### Level Score List

| Command Format | Aliases | Description | Example |
|----------------|---------|-------------|---------|
| `[Level]のレコードリスト` | `[Level]record-list`, `[Level]records` | View all scores for specified level | `13のレコードリスト` |
| `[Level]のレコードリスト [Page]` | `[Level]record-list [Page]`, `[Level]records [Page]` | View scores for level (page N) | `13のレコードリスト 2` |

**Note**: Level can be an integer (1-15) or decimal. Integer shows level list, decimal shows constant list.

---

## Version Achievements

### Plate Achievement Status

**Command Format**: `[Version Nameplate]の達成状況`

**Aliases**: Use `achievement-list` or `achievement` to replace `の達成状況`

| Plate Type | Example | Description |
|------------|---------|-------------|
| 極 (Extreme) | `宴極の達成状況` | View "宴極" plate achievement |
| 将 (Master) | `双将の達成状況` | View "双将" plate achievement |
| 神 (God) | `鏡神の達成状況` | View "鏡神" plate achievement |
| 舞舞 (Dancer) | `彩舞舞の達成状況` | View "彩舞舞" plate achievement |

**More Examples**:
```
宴極の達成状況                # 宴 Extreme
双将の達成状況                # 双 Master
鏡神の達成状況                # 鏡 God
彩舞舞の達成状況              # 彩 Dancer
真極の達成状況                # 真 Extreme
真将の達成状況                # 真 Master
真神の達成状況                # 真 God
真舞舞の達成状況              # 真 Dancer
```

**English Alias Examples**:
```
宴achievement-list            # Same as 宴極の達成状況
双achievement                 # Same as 双将の達成状況
```

### Version Song List

| Command Format | Aliases | Description | Example |
|----------------|---------|-------------|---------|
| `[Version]のバージョンリスト` | `[Version]version-list`, `[Version]version` | View all songs in that version | `PRiSM PLUSのバージョンリスト` |

**Version Examples**:
```
PRiSM PLUSのバージョンリスト
FESTiVAL PLUSのバージョンリスト
BUDDiESのバージョンリスト
UNiVERSEのバージョンリスト
```

---

## Friend Features

### Friend Management

| Command | Aliases | Description |
|---------|---------|-------------|
| `friend list` | `friendlist`, `フレンドリスト` | View added friends list |
| `add-friend [Code]` | `add friend [Code]`, `addfriend [Code]`, `フレンド追加 [Code]` | Add friend |
| `friend-b50 [Code]` | `friend b50 [Code]`, `フレンドb50 [Code]` | View friend's B50 |

**Examples**:
```
friend list                   # View friends list
add-friend 1234567890123456   # Add friend
friend-b50 1234567890123456   # View friend's B50
```

**Notes**:
- Friend code is 16 digits
- Requires SEGA account binding
- Friend data is automatically cached

---

## Utility Commands

### Rating Calculator

| Command | Description | Example |
|---------|-------------|---------|
| `rc [constant]` | View Rating table for specified constant | `rc 13.2` |
| `RC [constant]` | Rating table (uppercase) | `RC 13.2` |
| `Rc [constant]` | Rating table (capitalized) | `Rc 13.2` |

### Score Calculator

| Command | Description | Example |
|---------|-------------|---------|
| `calc [tap] [hold] [slide] [break]` | Calculate 4-key score (no touch) | `calc 500 100 200 50` |
| `calc [tap] [hold] [slide] [touch] [break]` | Calculate 5-key score (with touch) | `calc 500 100 200 50 50` |

**Notes**:
- Calculator shows achievement for various miss types (Great/Good/Miss)
- Supports both 4-parameter (no touch) and 5-parameter (with touch) formats

### Random Song

| Command | Description | Example |
|---------|-------------|---------|
| `ランダム曲` | Randomly select a song | `ランダム曲` |
| `random-song` | Randomly select a song (English) | `random-song` |
| `random` | Randomly select a song (short) | `random` |

### Card Generation

| Command | Aliases | Description |
|---------|---------|-------------|
| `maid card` | `maid`, `mai pass`, `maipass`, `マイパス`, `マイカード` | Generate maimai pass card |

### Image Recognition

| Feature | Description |
|---------|-------------|
| Send Image | Automatically scan QR codes in images to identify friend invite links or other data |

**Notes**:
- Send a screenshot of a friend's card to Bot, it will automatically recognize the friend invite link
- Supports scanning any image containing QR codes

### Location Service

| Feature | Description |
|---------|-------------|
| Send Location | Find nearby maimai arcades (up to 4 locations) |

**Notes**:
- In LINE, tap "+" button and select "Location"
- Send your current location or any location
- Bot will return nearby maimai arcade information (name, address, distance, map link)

---

## Admin Commands

**Note**: The following commands are admin-only

| Command | Description |
|---------|-------------|
| `upload notice [content]` | Upload new notice, reset all users' read status |
| `dxdata update` | Manually update dxdata database and compare changes |

---

## Quick Reference

### Common Commands

```
check                      # Check online status
bind                       # Bind SEGA account
update                     # Update score data
b50                        # View B50
ヒバナってどんな曲          # View song info
ヒバナのレコード            # View personal score
宴極の達成状況             # View Extreme achievement
friend list                # Friends list
maid card                  # Generate card
```

### Filter Examples

```
b50 -lv 13.2 13.8          # Constant 13.2-13.8
b50 -lv 13.2               # Constant ≥13.2 (no limit)
b50 -ra 301 312            # Rating 301-312
b50 -ra 301                # Rating ≥301 (no limit)
b50 -scr 100.3 100.8       # Achievement 100.3%-100.8%
b50 -scr 100.3             # Achievement ≥100.3% (no limit)
b50 -dx 92 95              # DX score 92%-95%
b50 -dx 92                 # DX score ≥92% (no limit)
```

---

**Last Updated**: 2025-10-27
**Version**: Generated from main.py analysis

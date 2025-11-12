# Song Search and Record Query

Find maimai DX song information, get random songs, and explore the complete song database.

## Song Information Search

Search by song name, abbreviation, or keywords to get detailed information.

### Basic Search

**Command Format:**

```
[song name] + info
[song name] + song-info
[song name] + ってどんな曲
```

**Examples:**

```
blew moon info
グリーンライツ・セレナーデ ってどんな曲
AMAZING MIGHTYYYY song-info
```

### Search Behavior

- **Fuzzy Matching**: Adopts intelligent matching (85% similarity threshold)
- **Multiple Results**: Displays up to 6 matching songs
- **Partial Name Matching**: For example, "amazing might" can match "AMAZING MIGHTYYYY!!!!!"

:::tip Search Tips
- Can use English or Japanese names
- Supports full names and abbreviations
- Case-insensitive
- Special symbols can usually be omitted
:::

### Display Content

Each result includes:

- 📝 **Song Title** (English & Japanese)
- 🎨 **Cover Art**
- 🎵 **Artist**
- 📅 **Version Information**
- 🎮 **Available Difficulties** (Basic / Advanced / Expert / Master / Re:MASTER)
- 📊 **Chart Constant**
- 🎯 **Chart Type** (Standard / DX)
- 🎬 **Category (Genre)**

---

## Random Song

Randomly get a song, with optional level specification.

### Basic Random

**Command Format:**

```
random
random-song
ランダム
ランダム曲
```

**Example:**

```
random
```

Randomly selects a song from the entire maimai DX song library.

### Random by Level

**Command Format:**

```
random [level]
random-song [level]
ランダム [level]
```

**Examples:**

```
random 14
ランダム曲 13+
random-song 15
```

### Level Filter Syntax

- `14` represents 14.0~14.4
- `13+` represents 13.5~13.9
- `14.6` represents only charts with a constant of 14.6

:::tip Random Challenge
You can use the random feature to:
- Practice challenges
- Discover new songs
- Break out of your usual music style
- Use as daily task goals
:::

---

## View Songs by Version

View all songs added in a specific maimai DX version.

**Command Format:**

```
[version name] + version
[version name] + version-list
[version name] + のバージョンリスト
```

**Examples:**

```
FESTiVAL version
BUDDiES PLUS のバージョンリスト
Splash version-list
でらっくす PLUS version
```

:::tip Tips
- `FESTiVAL+` will be automatically recognized as `FESTiVAL PLUS`
:::

**Display Content:**
- Song list

---

## Score Query

View your play records for a specific song.

**Command Format:**

```
[song name] + record
[song name] + song-record
[song name] + のレコード
```

**Examples:**

```
blew moon record
オンゲキ音頭 のレコード
AMAZING MIGHTYYYY song-record
```

:::warning Account Binding Required
Score features require binding your SEGA ID first. See [Account Binding](/en/guide/binding)
:::

**Display Content:**
- 📊 Achievement Rate
- 🎵 DX Score
- 🏆 Completion Status (FC / FC+ / AP / AP+)
- 💎 Sync Status (FS / FS+ / FDX / FDX+)
- 📈 Rating Contribution Value

If "Record Not Found" is displayed:
- May not have played this song
- Score not updated (try `maimai update`)
- Name matching error (try using info search first)

---

## View Scores by Level

View all scores for a specified level.

**Command Format:**

```
[level] + record-list
[level] + records
[level] + のレコードリスト
```

**Examples:**

```
14 record-list
13+ のレコードリスト
15 records
```

Pagination:
```
14 record-list 2
13+ のレコードリスト 3
```

:::tip Tips
Use level records to:
- Track high difficulty progress
- Find improvement opportunities
- Analyze weaknesses
- Set practice goals
:::

---

## Advanced Usage

### Find Similar Songs

1. Search for a song you like:
   ```
   blew moon info
   ```
2. Check the category or artist
3. View the song list from the same version to find similar works

### Discover New Songs

1. Random by level:
   ```
   random 13+
   ```
2. View song information
3. If already played, can directly check scores

### Practice Planning

1. Check songs by level:
   ```
   14 record-list
   ```
2. Find songs to improve
3. View chart details to assist practice

---

## Comparison: Search vs Score Query

| Feature | Song Info Search | Score Query |
|------|---------------|-----------|
| **Purpose** | Get song data | View personal scores |
| **Binding Required** | ❌ No | ✅ Yes |
| **Display Content** | Song information | Personal data |
| **Use Case** | Explore/learn about songs | Progress tracking |
| **Response Speed** | Fast | Fast (cached) |

:::tip Pro Tip
If you're sure about the song name, you can use the record command directly:
```
blew moon record
```
This will display both song information and scores at once!
:::

---

## Troubleshooting

### "Song Not Found"

**Possible Causes:**
- Spelling error
- Song is not part of maimai DX
- Version error (JP / International)

**Solutions:**
- Try different keywords
- Check [maimai wiki](https://maimai.fandom.com/)
- Try English or Japanese name

### Random Song Repetition

This is normal random probability. You can reduce repetition by filtering by level:
```
random 14+
```

### Version List Incomplete

**Possible Causes:**
- Incorrect name
- Database needs updating

**Solutions:**
- Check spelling
- Try alternative spelling
- Can report at [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

---

## Quick Reference

```bash
# Search
[song] info          # Check song information
[song] record        # Check personal score

# Random
random               # Random song
random 14            # Random Lv14

# Version
FESTiVAL version     # View FESTiVAL songs

# Level Scores
14 record-list       # Lv14 song scores
13+ records 2        # Page 2 of Lv13+ scores
```

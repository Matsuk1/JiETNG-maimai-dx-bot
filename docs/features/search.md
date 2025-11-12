# Song Search

Find information about maimai DX songs, get random songs, and explore the song database.

## Song Information Search

Search for songs by name, acronym, or keywords to get detailed information.

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

- **Fuzzy matching**: The bot uses intelligent matching (85% similarity threshold)
- **Multiple results**: Returns up to 6 matching songs
- **Acronyms supported**: Try "bm" for "Blew Moon", "gls" for "グリーンライツ・セレナーデ"
- **Partial names**: "amazing might" will find "AMAZING MIGHTYYYY!!!!!"

:::tip Search Tips
- Use English or Japanese names
- Both full names and abbreviations work
- The bot is case-insensitive
- Special characters are usually optional
:::

### What Information is Shown?

Each result displays:

- 📝 **Song title** (English and Japanese)
- 🎨 **Jacket image**
- 🎵 **Artist name**
- 📅 **Version** (when the song was added)
- 🎮 **Available difficulties** (Basic, Advanced, Expert, Master, Re:MASTER)
- 📊 **Chart constants** (internal level values)
- 🎯 **Chart type** (Standard/DX)
- 🎬 **Genre/Category**

### No Results?

If your search returns no results:

1. **Try different keywords**:
   - Use official song name
   - Try the Japanese name if English doesn't work
   - Use common abbreviations

2. **Check spelling**:
   - Verify character accuracy (especially for special symbols)
   - Try removing special characters

3. **Song might not exist**:
   - Make sure the song is in maimai DX (not other SEGA rhythm games)
   - Check if it's available in your version (jp/intl)

## Random Song

Get a random song suggestion, optionally filtered by difficulty level.

### Basic Random Song

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

Returns a random song from the entire maimai DX library.

### Random Song with Level Filter

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

You can specify:

- **Single level**: `14` (exactly 14.0-14.4)
- **Plus level**: `13+` (exactly 13.5-13.9)
- **Specific internal level**: `14.6` (only 14.6 charts)

The bot will randomly select from songs with ANY chart matching the specified level.

:::tip Random Challenge
Use random songs for:
- Practice challenges
- Discovery of new songs
- Breaking out of comfort zones
- Daily song goals
:::

## Version-Specific Songs

View all songs from a specific maimai DX version.

### Command Format

```
[version name] + version
[version name] + version-list
[version name] + のバージョンリスト
```

### Available Versions

Major versions:
- `maimai`, `maimai PLUS`
- `GreeN`, `GreeN PLUS`
- `ORANGE`, `ORANGE PLUS`
- `PiNK`, `PiNK PLUS`
- `MURASAKi`, `MURASAKi PLUS`
- `MiLK`, `MiLK PLUS`
- `FiNALE`
- `でらっくす` (Deluxe), `でらっくす PLUS`
- `Splash`, `Splash PLUS`
- `UNiVERSE`, `UNiVERSE PLUS`
- `FESTiVAL`, `FESTiVAL PLUS`
- `BUDDiES`, `BUDDiES PLUS`

**Examples:**

```
FESTiVAL version
BUDDiES PLUS のバージョンリスト
Splash version-list
でらっくす PLUS version
```

:::tip Version Names
- For PLUS versions, use a space: `FESTiVAL PLUS` ✅
- The bot will automatically handle `+` in input: `FESTiVAL+` → `FESTiVAL PLUS`
- Both English and Japanese names work
:::

### What You Get

The version list shows:
- All songs added in that version
- Song jackets
- Standard vs DX designation
- Difficulty levels available
- Artist names

## Song Records

Check your personal record on a specific song.

### Command Format

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

:::warning Binding Required
Song records require you to bind your SEGA ID. See [Account Binding](/guide/binding).
:::

### What's Shown

For each difficulty you've played:
- 📊 Achievement percentage
- 🎵 DX Score
- 🏆 Clear lamp (Clear, FC, FC+, AP, AP+)
- 💎 Sync status (FS, FS+, FDX, FDX+)
- 📈 Rating contribution
- 🎯 Accuracy breakdown (if available)

### No Record?

If you see "No record found":
- You haven't played this song yet
- Your scores haven't been updated (try `maimai update`)
- The song name might not match exactly (try using info search first)

## Level-Based Records

View all your records for songs of a specific level.

### Command Format

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

### Pagination

Records are split into pages (default: 50 per page).

Add a page number to see more:

```
14 record-list 2
13+ のレコードリスト 3
```

:::tip Finding Your Target Songs
Use level records to:
- Track progress on high-level charts
- Find songs to improve rating
- Identify weak spots in your gameplay
- Plan your grinding targets
:::

## Advanced Search Use Cases

### Finding Similar Songs

1. Search for a song you like:
   ```
   blew moon info
   ```

2. Note the genre/artist

3. Search version list to find similar songs from same update

### Discovering New Songs

1. Use random with your skill level:
   ```
   random 13+
   ```

2. Check the song info if interested

3. Look up your record if you've played it

### Practice Planning

1. Find songs in a level range:
   ```
   14 record-list
   ```

2. Identify songs with room for improvement

3. Look up specific song info for practice

## Comparison: Search vs Records

| Feature | Song Info Search | Song Records |
|---------|-----------------|-------------|
| **Purpose** | Get song data | Get YOUR scores |
| **Requires Binding** | ❌ No | ✅ Yes |
| **Shows** | Chart info | Your achievements |
| **Use Case** | Discovery | Progress tracking |
| **Speed** | Fast | Fast (cached) |

## Search Performance

- **Fuzzy matching**: Uses optimized algorithm (85% threshold)
- **Max results**: 6 songs per search
- **Response time**: Usually < 1 second
- **Cache**: Song database is cached in memory

:::tip Pro Tip
If you know the exact song name, use records instead of info to save time:
```
blew moon record
```
This shows both song info AND your scores in one command!
:::

## Troubleshooting

### "Song not found"

**Possible causes:**
- Typo in song name
- Song doesn't exist in maimai DX
- Wrong version (jp vs intl)

**Solutions:**
- Try different keywords
- Search on [maimai wiki](https://maimai.fandom.com/)
- Use English name instead of Japanese (or vice versa)

### Random Song Keeps Repeating

**Explanation:**
Random selection is truly random - repetition is normal probability.

**Workaround:**
Narrow down with level filters:
```
random 14+
```

### Version List is Incomplete

**Possible causes:**
- Version name typo
- Bot's song database needs updating

**Solutions:**
- Check spelling (e.g., `FESTiVAL` not `FESTIVAL`)
- Try alternative version names
- Report missing songs on [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

## Next Steps

- [Level Records](/features/level-records) - Explore level-based filtering
- [Plate Progress](/features/plates) - Track version achievements
- [Command Reference](/commands/basic) - All available commands
- [Advanced Filters](/commands/advanced) - Filter by rating, DX score, etc.

---

**Quick Reference:**

```bash
# Search
[song] info                    # Find song info
[song] record                  # Your score on this song

# Random
random                         # Any song
random 14                      # Random lv14 song

# Version
FESTiVAL version              # All FESTiVAL songs

# Level Records
14 record-list                # All your lv14 records
13+ records 2                 # Page 2 of lv13+ records
```

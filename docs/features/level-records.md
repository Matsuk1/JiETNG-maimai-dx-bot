# Level Records

View all your scores for songs of a specific difficulty level, paginated for easy browsing.

## Overview

Level Records let you:
- 📊 See all your scores at a specific level (e.g., all 14 charts)
- 📈 Track improvement within a level
- 🎯 Identify songs to improve for rating gains
- 🔍 Find weak spots in your skill range
- 📄 Browse through pages of results

:::warning Binding Required
You must [bind your SEGA ID](/guide/binding) and update scores to view level records.
:::

## Basic Usage

### Command Format

```
[level] + record-list
[level] + records
[level] + のレコードリスト
```

### Examples

```
14 record-list
13+ のレコードリスト
15 records
```

## Level Notation

### Standard Levels

- `11`, `12`, `13`, `14`, `15`

These show all charts with internal values:
- **11**: 11.0 - 11.4
- **12**: 12.0 - 12.4
- **13**: 13.0 - 13.4
- **14**: 14.0 - 14.4
- **15**: 15.0 - 15.4

### Plus Levels

- `11+`, `12+`, `13+`, `14+`, `15+`

These show all charts with internal values:
- **11+**: 11.5 - 11.9
- **12+**: 12.5 - 12.9
- **13+**: 13.5 - 13.9
- **14+**: 14.5 - 14.9
- **15+**: 15.5 - 15.9 (if exist)

:::tip Internal Levels
maimai DX uses internal level values like 13.7, 14.3, etc. The displayed level (13+, 14) groups these into ranges.
:::

## Pagination

### Default View

Running just `14 record-list` shows:
- **First page** (default)
- **Up to 50 songs** per page

### Accessing Other Pages

Add a page number to see more results:

```
14 record-list 2
13+ のレコードリスト 3
15 records 4
```

**Page numbering:**
- Page 1: Songs 1-50
- Page 2: Songs 51-100
- Page 3: Songs 101-150
- etc.

### Navigation Tips

If you have many songs at a level:

```bash
# Start with page 1
14 record-list

# If there are more songs (bot will indicate)
14 record-list 2
14 record-list 3
# ... and so on
```

## What Information is Shown

For each song in the level, you'll see:

### Basic Info
- 🎵 **Song Name**
- 🎨 **Jacket Image**
- 🎼 **Difficulty** (Basic/Advanced/Expert/Master/Re:MASTER)
- 📊 **Chart Type** (Standard/DX)

### Your Performance
- 📈 **Achievement %**: Your score percentage
- 🎵 **DX Score**: Your DX rating on this chart
- 🏆 **Clear Lamp**: Clear status
  - CLEAR
  - FC (Full Combo)
  - FC+ (Full Combo+)
  - AP (All Perfect)
  - AP+ (All Perfect+)
- 💎 **Sync Status**:
  - FS (Full Sync)
  - FS+ (Full Sync+)
  - FDX (Full Sync DX)
  - FDX+ (Full Sync DX+)
- 📊 **Rating Contribution**: How much rating this chart gives you

### Sort Order

Songs are typically sorted by:
1. **Rating** (highest first)
2. **Achievement %** (if rating is equal)
3. **Alphabetical** (as tiebreaker)

## Use Cases

### Use Case 1: Rating Improvement

**Goal**: Increase your rating by improving level 14 scores

**Process:**
```bash
# 1. View your 14 records
14 record-list

# 2. Identify songs with:
   - Low achievement (< 98%)
   - High internal level (14.4, 14.3)
   - In your B50 already (priority)

# 3. Practice those songs

# 4. Update scores
maimai update

# 5. Check improvement
14 record-list
```

### Use Case 2: Completion Tracking

**Goal**: Play all 14+ songs

**Process:**
```bash
# Check current plays
14+ record-list

# Note which songs are missing (not in the list)

# Look up all 14+ songs
# (Use external resources or song search)

# Play missing songs

# Verify completion
14+ record-list
```

### Use Case 3: Consistency Check

**Goal**: Ensure consistent performance across a level

**Process:**
```bash
# View all level 13 records
13 record-list

# Identify outliers:
   - Songs below 97% (weak spots)
   - Songs at 100% (strengths)
   - Large gaps in achievement

# Focus on bringing weak songs up
```

### Use Case 4: Plate Progress

**Goal**: Prepare for version plate at level 14

**Process:**
```bash
# 1. Check all your 14 records
14 record-list

# 2. Filter mentally for the target version

# 3. Identify songs below 97% from that version

# 4. Practice and improve those specific songs

# 5. Check version achievement
[version] achievement
```

## Combining with Filters

Level records can be combined with [advanced filters](/commands/advanced) for more specific queries.

### Examples with Filters

```bash
# All level 14 songs with rating above 200
b50 -lv 14 -ra 200

# All level 13+ songs with achievement below 98%
b50 -lv 13.5 13.9 -scr 0 98

# All level 14 songs with DX score above 90%
b50 -lv 14 -dx 90
```

See [Advanced Filters](/commands/advanced) for complete syntax.

## Tips & Strategies

### Finding Easy Rating Gains

1. **High internal level + low achievement = opportunity**
   - Example: 14.6 chart at 96% achievement
   - Improving to 98% gives significant rating boost

2. **Sort by rating contribution**
   - Focus on charts that could enter your B50
   - Prioritize songs with high base rating

3. **Compare to your B50**
   ```bash
   b50              # See your current top 50
   14 record-list   # See all your 14s
   ```
   - Find 14 songs NOT in your B50
   - Those are improvement opportunities

### Identifying Skill Gaps

**Consistently low on certain levels?**

```bash
13+ record-list   # Check your 13+ scores
14 record-list    # Check your 14 scores
```

Compare average achievements:
- 13+: Average 98.5%
- 14: Average 96.0%

**Gap identified!** Focus on level 14 practice.

### Breaking into New Levels

**Want to start playing 15?**

```bash
# 1. Check your 14+ performance
14+ record-list

# 2. If mostly 98%+ → Ready for 15
# 3. If mostly < 97% → Practice 14+ more

# 4. Start with easier 15 songs
15 record-list    # See which 15s you've tried
```

## Troubleshooting

### "No records found"

**Problem**: Level has no scores shown

**Causes:**
- Haven't played any songs at that level
- Scores haven't been updated
- Wrong level notation

**Solutions:**
```bash
# Update scores
maimai update

# Try again
14 record-list

# Try plus notation
14+ record-list

# Check other levels
13+ record-list
```

### Page is Empty

**Problem**: Page 2 or higher shows no songs

**Cause:** You don't have enough songs at that level for multiple pages

**Solution:** Check page 1 - all your songs are there!

### Songs Missing

**Problem**: Expected more songs in the level

**Causes:**
- Songs not played yet
- Songs are actually at different level (13+ vs 14)
- Scores not synced

**Solutions:**
```bash
# Check adjacent levels
13+ record-list
14 record-list
14+ record-list

# Update scores
maimai update

# Verify song level with search
[song name] info
```

## Pagination Example

**Scenario**: You have 120 songs at level 14

**Page 1 (default):**
```bash
14 record-list
# Shows songs 1-50
# Note at bottom: "Page 1 of 3"
```

**Page 2:**
```bash
14 record-list 2
# Shows songs 51-100
# Note at bottom: "Page 2 of 3"
```

**Page 3:**
```bash
14 record-list 3
# Shows songs 101-120
# Note at bottom: "Page 3 of 3"
```

**Page 4 (doesn't exist):**
```bash
14 record-list 4
# Empty or error message
```

## Performance Notes

- **Fast retrieval**: Records are cached for quick access
- **Bulk load**: All levels loaded at once when you update
- **Real-time**: Shows most recent synced data
- **No API calls**: Queries local database (fast!)

## Related Features

### Song Records

Check individual song scores:
```bash
[song name] record
```

See [Song Search](/features/search#song-records) for details.

### Best 50

View your top-rated songs:
```bash
b50      # Top 50 songs
b35      # Top 35 old songs
b15      # Top 15 new songs
```

See [Best 50](/features/b50) for details.

### Filtered Records

Apply advanced filters:
```bash
b50 -lv 14 14.9 -ra 200
```

See [Advanced Filters](/commands/advanced) for syntax.

## Advanced Usage

### Comparing Across Levels

Check multiple levels to see skill distribution:

```bash
13 record-list    # Count: ~80 songs, avg 98.5%
13+ record-list   # Count: ~60 songs, avg 98.0%
14 record-list    # Count: ~40 songs, avg 96.5%
14+ record-list   # Count: ~20 songs, avg 95.0%
15 record-list    # Count: ~5 songs, avg 93.0%
```

**Analysis:**
- Strong at 13/13+ (many songs, high %)
- Transitioning to 14 (decent coverage)
- Struggling with 14+ (fewer songs, lower %)
- Just starting 15 (very few songs)

**Action plan:**
- Maintain 13+ level (occasional practice)
- Focus on 14+ (most improvement potential)
- Slowly increase 15 exposure

### Export and Analysis

**Manual method:**
1. Take screenshots of each page
2. Compile into a spreadsheet
3. Add formulas for analysis
4. Track over time

**Automated method** (if supported):
- Use bot's export feature
- Download CSV/JSON
- Analyze with tools (Excel, Python, etc.)

## Next Steps

- [Advanced Filters](/commands/advanced) - Filter by rating, score, DX score
- [Best 50](/features/b50) - Your top-rated songs
- [Plate Progress](/features/plates) - Version completion tracking

---

**Quick Reference:**

```bash
# View level records
[level] record-list
[level] のレコードリスト

# Examples
14 record-list           # All level 14 songs (page 1)
13+ record-list 2        # Level 13+ songs (page 2)
15 records               # All level 15 songs

# Related
[song] record            # Single song record
b50 -lv 14               # Best songs at level 14 (with filters)
maimai update            # Update scores first
```

**Pro Tips:**
- Update scores before checking records: `maimai update` → `14 record-list`
- Use pagination for large lists: `14 record-list 2`
- Compare adjacent levels to find skill gaps: `13+ record-list` vs `14 record-list`
- Focus on high internal levels for rating gains (14.5+, 14.6, etc.)

# Plate Progress Tracking

Track your achievement progress for maimai DX version plates and see which songs you need to complete.

## What are Plates?

Plates (称号 / しょうごう) are achievement titles in maimai DX earned by completing specific goals:

- **Version Plates**: Complete all songs from a specific version
- **Difficulty Plates**: Clear all charts of a certain difficulty
- **Special Plates**: Meet unique conditions (All FC, All AP, etc.)

Each plate has different requirements:
- 🎵 Play all songs in the category
- 📊 Reach minimum achievement threshold (often 97%+)
- 🏆 Meet special conditions (Full Combo, All Perfect, etc.)

:::tip Why Track Plates?
- Goal-oriented progression
- Completion satisfaction
- Community recognition
- Unlock titles in-game
:::

## Checking Plate Progress

### Command Format

```
[version name] + achievement
[version name] + achievement-list
[version name] + の達成状況
[version name] + の達成情報
[version name] + の達成表
```

### Examples

```
FESTiVAL achievement
BUDDiES の達成状況
Splash achievement-list
でらっくす PLUS の達成情報
```

:::warning Binding Required
Plate tracking requires:
- [Bound SEGA ID](/guide/binding)
- Updated score data (`maimai update`)
:::

## Available Versions

### maimai DX Versions

Current and recent versions:

- `BUDDiES` / `BUDDiES PLUS`
- `FESTiVAL` / `FESTiVAL PLUS`
- `UNiVERSE` / `UNiVERSE PLUS`
- `Splash` / `Splash PLUS`
- `でらっくす` (Deluxe) / `でらっくす PLUS`

### Classic maimai Versions

Older versions (may have limited song availability):

- `FiNALE`
- `MiLK` / `MiLK PLUS`
- `MURASAKi` / `MURASAKi PLUS`
- `PiNK` / `PiNK PLUS`
- `ORANGE` / `ORANGE PLUS`
- `GreeN` / `GreeN PLUS`
- `maimai` / `maimai PLUS`

:::tip Version Names
- Use exact capitalization: `FESTiVAL` not `Festival`
- For PLUS versions: `FESTiVAL PLUS` (space, not `+`)
- Japanese names also work: `でらっくす`
:::

## Understanding the Achievement Chart

The plate progress chart shows:

### Overall Progress

- **Completion Percentage**: How close you are to the plate
- **Songs Completed**: Number of songs meeting requirements
- **Songs Remaining**: What you still need to do
- **Target Threshold**: Required achievement % (usually 97%+)

### Song-by-Song Breakdown

For each song in the version:

- ✅ **Completed**: Met the requirements
- ❌ **Not Completed**: Below threshold or not played
- 🎵 **Song Name**: Which song it is
- 📊 **Your Achievement**: Current score percentage
- 🎯 **Target**: What you need to reach
- 📈 **Gap**: How far you are from target

### Difficulty Breakdown

Some plates show progress per difficulty:
- Basic
- Advanced
- Expert
- Master
- Re:MASTER

## Plate Requirements

### Standard Version Plates

Most version plates require:

**Requirement**: Play all songs from the version and achieve **97%+** on any difficulty

**Example: FESTiVAL Plate**
- All FESTiVAL songs (e.g., 50 songs)
- Each song at 97.0000% or higher
- Any difficulty counts (Basic, Advanced, Expert, Master, Re:MASTER)
- One difficulty per song is enough

:::tip Smart Strategy
For version plates, you can:
- Play the easiest difficulty for each song
- Focus on getting 97%+ rather than high difficulty
- Use Advanced or Expert instead of Master
- Save time while completing plates
:::

### Full Combo (FC) Plates

**Requirement**: Full Combo on all songs in a version/difficulty

**What counts as Full Combo:**
- No misses (GREAT or better on all notes)
- FC or FC+ lamp

**Tips:**
- Start with easier difficulties (Advanced/Expert)
- Use player-friendly songs
- Practice trouble spots separately
- Consider barrier songs (known difficult FC songs)

### All Perfect (AP) Plates

**Requirement**: All Perfect on all songs

**What counts as All Perfect:**
- Only CRITICAL PERFECT notes (no PERFECT or below)
- AP or AP+ lamp

**Tips:**
- Much harder than FC plates
- Requires precision and consistency
- Start with slower BPM songs
- May take months or years to complete

### Special Plates

Some plates have unique requirements:
- Play all songs at specific level (e.g., "All Master 14")
- Achieve certain rating threshold
- Complete with specific conditions (no GOOD, etc.)

Check in-game or community resources for specific plate requirements.

## Strategies for Plate Completion

### Step 1: Check Current Progress

```bash
# See what you've already completed
FESTiVAL achievement
```

Review:
- How many songs are done
- Which songs are closest to completion
- Which songs you haven't played

### Step 2: Prioritize Low-Hanging Fruit

Focus on songs where you're close:
- 96.5% → Need just 0.5% more
- 95% → More practice needed
- Not played → High priority

**Command to check specific songs:**
```bash
[song name] record
```

### Step 3: Practice and Improve

For songs below threshold:
1. Identify problem sections
2. Practice in-game (track mode)
3. Study chart videos online
4. Adjust settings (speed, touch settings)
5. Retry until 97%+

### Step 4: Update and Track

After playing:

```bash
# Update scores
maimai update

# Check progress again
FESTiVAL achievement
```

Repeat until plate complete!

## Achievement Tips

### Getting 97% Consistently

**Technical tips:**
- **Timing**: Adjust audio offset if early/late
- **Speed**: Find optimal scroll speed (default vs fast)
- **Touch**: Calibrate touch sensitivity
- **Grip**: Use consistent grip and hand position

**Practice tips:**
- **Warm up**: Play easier songs first
- **Focus**: Minimize distractions during play
- **Rest**: Take breaks to avoid fatigue
- **Review**: Watch replays to find mistakes

### Difficult Songs

**Barrier songs** (songs that block plate completion):

Common barriers:
- High BPM songs (180+)
- Dense charts with fast slides
- Awkward patterns (cross-hands, etc.)
- Touch-heavy charts

**Overcoming barriers:**
1. **Accept it takes time**: Some songs need weeks of practice
2. **Break it down**: Practice sections separately
3. **Study**: Watch videos of skilled players
4. **Alternatives**: Try different difficulties
5. **Community**: Ask for tips in Discord/forums

### Efficiency

**Fastest plate completion:**
1. Play easiest difficulty for each song (Advanced/Expert)
2. Skip Master/Re:MASTER unless required
3. Focus on 97% threshold, not 100%
4. Use guides to identify easy songs
5. Batch similar songs together (same BPM/style)

## Tracking Multiple Plates

### Current Version Focus

Most players focus on:
- Latest version (BUDDiES, FESTiVAL, etc.)
- One version behind
- Popular classic versions (でらっくす, FiNALE)

### Progress Overview

Check multiple versions:

```bash
BUDDiES achievement        # Current version
FESTiVAL achievement       # Previous version
Splash achievement         # Older version
```

**Create a personal checklist:**
```
✅ FESTiVAL Plate: 100% (50/50 songs)
🔄 BUDDiES Plate: 85% (42/50 songs) - IN PROGRESS
⏳ Splash Plate: 60% (30/50 songs) - Future goal
```

## Community & Competition

### Sharing Progress

Post your plate achievements:
- Screenshots of completion
- Progress percentages
- Difficult songs conquered
- Time taken to complete

**Common places to share:**
- Discord servers (#achievements channel)
- Twitter with #maimai hashtag
- Reddit r/maimai
- Japanese communities (2ch, 5ch)

### Plate Race

Compete with friends:
- Who can complete plates fastest
- Race to complete new version plates
- Challenge each other on specific songs

```bash
# Check friend's progress (if they share)
friend-b50 [friend_code]

# Compare completion rates
```

## Troubleshooting

### "Version not found"

**Problem**: Can't check achievement for a version

**Causes:**
- Version name typo
- Unsupported version
- Case sensitivity issue

**Solutions:**
- Check spelling: `FESTiVAL` not `Festival`
- Try Japanese name: `でらっくす`
- Use space for PLUS: `FESTiVAL PLUS`
- Check available versions in [search docs](/features/search)

### Progress Not Updating

**Problem**: Played songs but progress doesn't change

**Cause**: Scores not updated in bot

**Solution:**
```bash
# 1. Update scores from maimai NET
maimai update

# 2. Wait for completion

# 3. Check plate progress again
FESTiVAL achievement
```

### Song Not Counted

**Problem**: Achieved 97% but song shows incomplete

**Possible causes:**
- Score was on wrong difficulty (if plate specifies)
- Achievement was exactly 97.000% but plate needs >97%
- Score data sync issue
- Song is not actually in that version

**Solutions:**
- Verify song is in the correct version
- Check if you need 97% or higher (97.0001%+)
- Try updating scores again
- Check the song's version in [version list](/features/search#version-specific-songs)

## Advanced Plate Features

### Filtering by Achievement Status

Some commands may support filters:

```bash
# All songs in version
FESTiVAL version

# Only incomplete songs (if supported)
FESTiVAL achievement-list incomplete
```

:::tip Feature Availability
Check if your bot version supports these filters. If not, manually review the complete list.
:::

### Exporting Plate Progress

Save your progress for later reference:
- Take screenshots
- Export to spreadsheet (manual)
- Use bot's export features (if available)

## Next Steps

- [Level Records](/features/level-records) - Track scores by difficulty
- [Best 50](/features/b50) - Overall rating progress
- [Song Search](/features/search) - Find specific songs
- [Advanced Filters](/commands/advanced) - Filter score lists

---

**Quick Reference:**

```bash
# Check plate progress
[version] achievement
[version] の達成状況

# Examples
FESTiVAL achievement
BUDDiES PLUS の達成情報
でらっくす achievement-list

# Related commands
[version] version          # See all songs in version
[song] record              # Check specific song score
maimai update              # Update scores from maimai NET
```

**Pro Tips:**
- Focus on one plate at a time
- Start with recent versions (more songs available)
- Use Advanced difficulty for faster completion
- Track progress weekly
- Celebrate milestones! 🎉

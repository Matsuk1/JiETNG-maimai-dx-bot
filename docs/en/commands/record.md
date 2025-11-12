# Score System

Best 50 (b50) and Best 100 (b100) charts are fundamental features of JiETNG, displaying your highest-rated scores with beautifully designed visualizations.

## What is Best 50?

The "Best 50" system is Maimai DX's official ranking method, consisting of:

- **Best 35**: Your top 35 highest scores in **Standard songs (songs from previous versions)**
- **Best 15**: Your top 15 highest scores in **DX songs (songs from current version)**

Your **Maimai DX Rating** is the sum of these 50 scores.

## Commands

### Basic Best Charts

```
b50          # Generate Best 50 chart
b100         # Generate Best 100 chart
best50       # Alternative command for b50
best100      # Alternative command for b100
```

### Variations

```
best35       # Show only top 35 Standard songs
best15       # Show only top 15 DX songs
ab50         # All Best 50 (ignore song version)
ab35         # All Best 35 (ignore song version)
apb50        # All Perfect Best 50 (AP/AP+ scores only)
idlb50       # Ideal Best 50 (simulate best scores)
```

## Chart Features

### What's Displayed

Each score card displays:

- <µ **Song name** and difficulty
- <® **Song version**: Standard or DX
- P **Internal constant**: e.g., 14.7
- =¯ **Achievement rate**: Your score percentage
- <Æ **Rank grade**: SSS+, SSS, SS+, etc.
- < **Full Combo type**: AP+, AP, FC+, FC
- =% **Full Sync**: FDX+, FDX, FS+, FS
- =Ê **Rating**: Single song rating
- =È **DX Rating**: Your DX Rating

### User Info Header

Charts include your profile:

- =d Player name and avatar
- <Å Dan/Class
- P Total rating
- <– Title

## Advanced Usage

### Filtering Scores

You can apply filters to customize b50 output:

#### Filter by Level

```
b50 -lv 15              # Only level 15 songs
b50 -lv 14 15           # Level 14-15
b50 -lv 13+             # Level 13.7+ and above
```

#### Filter by Rating

```
b50 -ra 200             # Only Rating 200+
b50 -ra 180 200         # Rating 180-200
```

#### Filter by Achievement Rate

```
b50 -scr 100.5          # Achievement rate 100.5%+
b50 -scr 99 100         # Achievement rate 99%-100%
```

#### Filter by DX Score

```
b50 -dx 95              # DX score 95%+
b50 -dx 90 95           # DX score 90-95%
```

### Combining Filters

You can combine multiple filters:

```
b50 -lv 15 -scr 100.5            # Level 15 with achievement rate 100.5%+
b50 -ra 200 -dx 95               # Rating 200+ with DX score 95%+
b50 -lv 14 15 -scr 99.5 -dx 90   # Complex filtering
```

## Chart Type Explanations

### Best 50 (b50)

Standard ranking chart following official rules:
- Top 35 from old version songs
- Top 15 from new version songs
- Your actual DX rating

**Use case**: View your official rating and progress

### Best 100 (b100)

Extended version showing more scores:
- Top 70 from old version songs
- Top 30 from new version songs

**Use case**: Find songs just below your b50 threshold

### All Best 50 (ab50)

Ignores song version distinction:
- Top 50 highest scores regardless of version

**Use case**: View highest achievements without version separation

### All Perfect Best 50 (apb50)

Shows only AP songs:
- Only AP (All Perfect) and AP+ scores
- Ranked by rating

**Use case**: Monitor your AP progress

### Ideal Best 50 (idlb50)

Theoretical maximum rating:
- Simulates previous tier scores for all songs
- Shows potential rating growth

**Use case**: Set goals for rating improvement


## FAQ

### Why is my rating different from in-game?

- JiETNG only updates when you run `maimai update`
- Some song constants may not be standard

### Some scores are missing?

Make sure you've played these songs recently. Older scores may not appear if:
- They've been replaced by better scores
- Songs have been removed from the game
- Data sync issues (try `maimai update` again)


## Related Features

- = [Score Search](/en/features/search) - Search for specific songs

---

Next: [Learn about advanced score search ’](/en/features/search)

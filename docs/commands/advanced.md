# Advanced Filtering

Use powerful filters to query your scores with precision - filter by level, rating, DX score, and achievement percentage.

## Overview

Advanced filters let you:
- 🎯 Find songs matching specific criteria
- 📊 Analyze score distributions
- 🔍 Identify improvement opportunities
- 📈 Target rating gains
- 🎮 Plan practice sessions

All filters work with Best 50 variants and record queries.

:::tip When to Use Filters
- Finding songs just below a threshold (97%, 98%)
- Identifying rating improvement targets
- Analyzing performance at specific levels
- Planning grinding sessions
:::

## Filter Syntax

### Basic Format

```
[base command] -[filter] [value(s)]
```

**Multiple filters:**
```
[base command] -[filter1] [value] -[filter2] [value]
```

### Available Filters

| Filter | Purpose | Value Format |
|--------|---------|--------------|
| `-lv` | Chart level | Single or range |
| `-ra` | Rating contribution | Single or range |
| `-dx` | DX Score % | Single or range |
| `-scr` | Achievement % | Single or range |

## Level Filter (`-lv`)

Filter songs by chart internal level.

### Single Level

**Syntax:**
```
b50 -lv [level]
```

**Examples:**
```
b50 -lv 14
b50 -lv 13.5
b50 -lv 14.6
```

**What it matches:**
- `-lv 14` → All charts with 14.0 ≤ level ≤ 14.9
- `-lv 13.5` → All charts with level exactly 13.5
- `-lv 14.6` → All charts with level exactly 14.6

### Level Range

**Syntax:**
```
b50 -lv [start] [end]
```

**Examples:**
```
b50 -lv 13 14
b50 -lv 14.0 14.4
b50 -lv 13.5 13.9
```

**What it matches:**
- `-lv 13 14` → Charts from 13.0 to 14.9
- `-lv 14.0 14.4` → Charts from 14.0 to 14.4 (standard 14)
- `-lv 13.5 13.9` → Charts from 13.5 to 13.9 (13+)

:::tip Level Ranges
- **Standard levels**: Use `.0` to `.4` (e.g., `14.0 14.4`)
- **Plus levels**: Use `.5` to `.9` (e.g., `13.5 13.9`)
- **Full range**: Use integers (e.g., `13 14`)
:::

### Use Cases

**Find all 14+ songs in your B50:**
```
b50 -lv 14.5 14.9
```

**Check performance on exactly 14.6 charts:**
```
b50 -lv 14.6
```

**View mid-level songs (13-14 range):**
```
b50 -lv 13 14
```

## Rating Filter (`-ra`)

Filter songs by rating contribution.

### Single Rating Threshold

**Syntax:**
```
b50 -ra [rating]
```

**Examples:**
```
b50 -ra 200
b50 -ra 150
ab50 -ra 180
```

**What it matches:**
- `-ra 200` → All charts giving 200+ rating
- `-ra 150` → All charts giving 150+ rating

### Rating Range

**Syntax:**
```
b50 -ra [min] [max]
```

**Examples:**
```
b50 -ra 180 220
b50 -ra 200 250
```

**What it matches:**
- `-ra 180 220` → Charts giving 180-220 rating
- `-ra 200 250` → Charts giving 200-250 rating

### Use Cases

**Find songs giving 200+ rating:**
```
b50 -ra 200
```

**Songs just below your B50 cutoff:**
```
# If your B50 cutoff is ~180 rating
ab50 -ra 170 179
```

**High-value songs for rating gains:**
```
b50 -ra 220
```

:::tip Rating and Level Relationship
Higher internal levels generally give more rating, but achievement % matters too:
- 14.6 at 97% = ~198 rating
- 14.6 at 100% = ~216 rating
- 15.0 at 97% = ~205 rating
:::

## DX Score Filter (`-dx`)

Filter songs by DX Score percentage (technical performance).

### Single DX Threshold

**Syntax:**
```
b50 -dx [percentage]
```

**Examples:**
```
b50 -dx 90
b50 -dx 85
b50 -dx 95
```

**What it matches:**
- `-dx 90` → All charts with DX Score ≥ 90%
- `-dx 85` → All charts with DX Score ≥ 85%

### DX Score Range

**Syntax:**
```
b50 -dx [min] [max]
```

**Examples:**
```
b50 -dx 85 95
b50 -dx 90 100
```

**What it matches:**
- `-dx 85 95` → Charts with DX Score between 85% and 95%
- `-dx 90 100` → Charts with DX Score between 90% and 100%

### Use Cases

**Find songs with low DX Score (accuracy issues):**
```
b50 -dx 0 85
```

**Songs with great DX Score:**
```
b50 -dx 95
```

**Identify songs needing better accuracy:**
```
b50 -lv 14 -dx 0 88
# Level 14 songs where you have < 88% DX Score
```

:::tip DX Score Meaning
- **90%+**: Excellent accuracy
- **85-90%**: Good, room for improvement
- **80-85%**: Many GOOD/GREAT notes
- **<80%**: Struggling with accuracy

DX Score is separate from achievement % - you can have 98% achievement but only 85% DX Score!
:::

## Achievement Score Filter (`-scr`)

Filter songs by achievement percentage (達成率).

### Single Achievement Threshold

**Syntax:**
```
b50 -scr [percentage]
```

**Examples:**
```
b50 -scr 98
b50 -scr 97
b50 -scr 99.5
```

**What it matches:**
- `-scr 98` → All charts with achievement ≥ 98%
- `-scr 97` → All charts with achievement ≥ 97%

### Achievement Range

**Syntax:**
```
b50 -scr [min] [max]
```

**Examples:**
```
b50 -scr 97 98
b50 -scr 95 97
b50 -scr 99 100
```

**What it matches:**
- `-scr 97 98` → Charts with 97-98% achievement
- `-scr 95 97` → Charts with 95-97% achievement
- `-scr 99 100` → Charts with 99-100% achievement

### Use Cases

**Find songs just below 98%:**
```
b50 -scr 97 98
# Songs you can improve to 98%+ for rating gains
```

**Songs ready for FC attempts:**
```
b50 -scr 99
# High achievement = few mistakes = FC-able
```

**Struggling songs:**
```
b50 -lv 14 -scr 0 96
# Level 14 songs below 96% achievement
```

## Combining Filters

The real power comes from combining multiple filters.

### Example 1: Rating Improvement Targets

**Goal**: Find level 14 songs with good potential for rating gains

```
b50 -lv 14 -scr 95 97.5
```

**Logic**:
- Level 14 songs (high base rating)
- Achievement 95-97.5% (room to improve to 98%+)
- Improving these gives significant rating boost

### Example 2: Accuracy Practice Targets

**Goal**: Find high-level songs where you need better accuracy

```
b50 -lv 14 -dx 0 88
```

**Logic**:
- Level 14 songs (your skill level)
- DX Score below 88% (poor accuracy)
- Practice these to improve technical skills

### Example 3: Near-Miss Songs

**Goal**: Find songs almost in your B50

```
ab50 -ra 180 195 -scr 96 98
```

**Logic**:
- Check all your songs (ab50)
- Rating 180-195 (near your B50 cutoff)
- Achievement 96-98% (improvable)
- Small improvement pushes them into B50

### Example 4: Perfect Practice Songs

**Goal**: Find songs to practice for AP/AP+

```
b50 -lv 13 -scr 99.5
```

**Logic**:
- Level 13 (manageable difficulty)
- Achievement 99.5%+ (very few mistakes)
- Good candidates for AP attempts

### Example 5: Grinding Candidates

**Goal**: Find specific songs to grind for maximum rating gains

```
b50 -lv 14.6 -ra 180 200 -scr 96 98
```

**Logic**:
- Level 14.6 (highest value)
- Rating 180-200 (good base, not perfect)
- Achievement 96-98% (clear improvement path)
- Focus grinding here for best rating return

## Common Filter Patterns

### Pattern: "Low-Hanging Fruit"

Songs easy to improve for quick rating gains:

```
b50 -lv 14 -scr 97 97.5 -ra 190
```

- High level (14)
- Just below 98% (achievable improvement)
- Already give decent rating

### Pattern: "Skill Gap Identifier"

Find levels where you're underperforming:

```
b50 -lv 14 -scr 0 95
```

Compare to:
```
b50 -lv 13 -scr 0 95
```

If 14 has many more songs, you have a level 14 skill gap.

### Pattern: "Consistency Check"

Check consistency within a level:

```
b50 -lv 14 -scr 98          # Your best 14s
b50 -lv 14 -scr 95 96       # Your weakest 14s
```

Large gap = inconsistent performance.

### Pattern: "Rating Optimizer"

Find best rating improvement opportunities:

```
# Step 1: Find high-value songs not in B50
ab50 -lv 14.5 14.9 -ra 200

# Step 2: Filter for improvable
ab50 -lv 14.5 14.9 -ra 200 -scr 95 98

# Step 3: Practice these specifically
```

## Filter Application Examples

### B50 Variants

All B50 variants support filters:

```
b50 -lv 14                   # Best 50 with level 14 songs
b100 -scr 99                 # Best 100 with 99%+ achievement
b35 -ra 200                  # Best 35 (old) with 200+ rating
b15 -lv 15                   # Best 15 (new) at level 15
ab50 -lv 13 14               # All best 50 at levels 13-14
idealb50 -lv 14.5            # Ideal best 50 at 14.5
```

### Special Commands

```
ap50 -lv 13                  # All Perfect songs at level 13
rct50 -scr 98                # Recent 50 with 98%+ achievement
unknown -lv 14               # Unknown songs at level 14
```

## Tips & Best Practices

### Efficient Filtering

1. **Start broad, narrow down**:
   ```
   b50 -lv 14          # See all your 14s
   b50 -lv 14 -scr 97  # Narrow to improvable
   ```

2. **Use realistic ranges**:
   ```
   # Good
   b50 -scr 97 98.5

   # Too narrow (may return nothing)
   b50 -scr 97.5 97.6
   ```

3. **Combine meaningfully**:
   ```
   # Makes sense
   b50 -lv 14 -ra 200

   # Contradictory (14.6 can't give <150 rating at 97%+)
   b50 -lv 14.6 -ra 0 150
   ```

### Understanding Results

- **Empty result**: Filters too strict or no songs match
- **Many results**: Broaden your goal or be more specific
- **Unexpected results**: Check filter logic

### Performance Considerations

- Filters are fast (local processing)
- No API calls needed
- Results return instantly
- Can apply complex multi-filter queries

## Troubleshooting

### No Results Returned

**Problem**: Filter returns empty

**Causes:**
- No songs match criteria
- Filters too restrictive
- Typo in command

**Solutions:**
```
# Broaden filter
b50 -lv 14 -scr 95        # Instead of -scr 99

# Check individual filters
b50 -lv 14                # Does this work?
b50 -scr 97               # Does this work?

# Verify filter syntax
b50 -lv 14 14.9           # Correct range format
```

### Unexpected Results

**Problem**: Results don't seem to match filter

**Causes:**
- Misunderstanding filter logic
- Inclusive vs exclusive ranges
- Decimal precision

**Solutions:**
- Double-check what filter means (≥ vs = vs range)
- Verify internal level values (use `[song] info`)
- Check achievement precision (97.0000% vs 97.5%)

### Filter Syntax Error

**Problem**: Command not recognized

**Causes:**
- Missing space after filter flag
- Wrong filter name
- Incorrect value format

**Solutions:**
```
# Wrong
b50 -lv14              # Missing space
b50 -level 14          # Wrong flag name
b50 -lv 14.           # Incomplete decimal

# Correct
b50 -lv 14
b50 -lv 14.0
b50 -lv 14.5 14.9
```

## Advanced Techniques

### Multi-Stage Filtering

Use filters progressively:

```bash
# Stage 1: Identify level range
b50 -lv 14

# Stage 2: Check which need improvement
b50 -lv 14 -scr 96 98

# Stage 3: Find high-value targets
b50 -lv 14 -scr 96 98 -ra 190
```

### Comparative Analysis

Compare different filter sets:

```bash
# High-level, high-achievement
b50 -lv 14.5 -scr 99

# High-level, low-achievement
b50 -lv 14.5 -scr 95 97

# Difference shows consistency
```

### Goal-Oriented Filtering

**Goal**: Reach 15000 rating

```bash
# 1. Check current high-value songs
b50 -ra 220

# 2. Find songs that could reach 220
ab50 -lv 14.6 -scr 98

# 3. Calculate needed improvements
# 4. Create practice plan
```

## Next Steps

- [Level Records](/features/level-records) - Browse by level
- [Best 50](/features/b50) - Core ranking feature
- [Basic Commands](/commands/basic) - Essential commands

---

**Quick Reference:**

```bash
# Filter Syntax
[command] -[filter] [value]
[command] -[filter1] [value1] -[filter2] [value2]

# Filters
-lv [level]              # Level filter (single or range)
-ra [rating]             # Rating filter (single or range)
-dx [percentage]         # DX Score filter (single or range)
-scr [percentage]        # Achievement filter (single or range)

# Examples
b50 -lv 14               # B50 songs at level 14
b50 -scr 97 98           # B50 songs with 97-98% achievement
b50 -lv 14 -ra 200       # Level 14 songs with 200+ rating
ab50 -lv 13 14 -scr 95   # All songs level 13-14 with 95%+ achievement
```

**Pro Tips:**
- Combine filters for precise queries
- Use ranges to find improvement targets
- Start broad, then narrow down
- Save successful filter combinations for regular use

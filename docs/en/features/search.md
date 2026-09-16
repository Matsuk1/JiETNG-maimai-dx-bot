---
title: maimai DX Search and Filtering
description: JiETNG supports maimai B50 filters, constants, levels, DX Rating, achievement, rating breakdown, and song record search.
---

# Search and Filtering

JiETNG search is split into score image filters, song search, and song ID lookup.

## Score Filters

```text
b50 -lv 14 14.9 -diff mas rem -scr 100.5
ab50 -ver buddies -type dx
ab50 -page 2
ap50 -lv 13.6
```

You can filter by level/constant, chart rating, achievement, DX score, DX stars, difficulty, chart type, version, and page.

The result is still rendered as a score image, which is useful for constant-range B50, MAS/Re:MAS-only lists, or version-specific views.

## Song Search

```text
artist Nanahira
designer Jack
bpm 180
bpm 0-120
bpm 120-180
ヒバナ info
```

- `artist` searches by artist.
- `designer` searches by chart designer.
- `bpm` searches by exact BPM or range; ranges can start from `0`, and `120-180`, `120~180`, and `120 180` are supported.
- `info` shows song details.
- Keywords are case-insensitive.

## Song Records

```text
ヒバナ record
```

`record` searches your record by title or alias.

## Data Source

Queries use processed records currently saved in JiETNG. They may come from:

- `maimai update`
- bookmarklet uploads with Import Token
- third-party uploads authenticated with a user Import Token

Query commands do not automatically resync official data.

## Choose the right query

`info`, `artist`, `designer`, `bpm`, and `random` use song data without requiring your scores to be synced. `record`, `records`, and B-series use stored personal data. The user's JP/INTL setting selects the dataset; the usual fallback is JP.

Use `artist Nanahira 2` or `designer Jack 2` for another page. Explicit BPM ranges avoid ambiguity: `bpm 120-180 2`; `bpm 180 2` means exact BPM 180, page 2, whereas `bpm 120 180` is a range.

Song matching supports titles and aliases. Normal search is capped at 10 candidates; narrow overly broad queries. Use the returned song-info/record/Calc buttons instead of typing their internal action names.

Use `14` or `14+` for levels and `14.7` for a constant. `-ver` matches version names, not arbitrary substrings. See [record commands](/en/commands/record) for precise filters.

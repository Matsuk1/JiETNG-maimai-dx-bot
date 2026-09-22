---
title: B50 Record Commands
description: JiETNG maimai DX B50, Best 50, Recent 50, DX Rating, rating breakdown, level targets, and song record command reference.
---

# Record Commands

<img src="/b50_example.jpg" alt="Best 50" style="max-width: 280px; width: 100%; margin: 24px auto;" />

## B-series images

| Command | Behavior |
|---|---|
| `b50` / `best50` | 35 old + 15 new charts |
| `b40` / `best40` | 25 old + 15 new charts, with the legacy Rating calculation |
| `b35` / `best35` | Old-chart Best 35 |
| `b15` / `best15` | New-chart Best 15 |
| `ab35` / `allb35` / `ab50` / `allb50` | Top 35 / 50 without old/new separation |
| `apb50` / `ap50` | AP/AP+ only, 35 old + 15 new |
| `fdxb50` / `fdx50` | FDX/FDX+ only, 35 old + 15 new |
| `rct50` / `r50` | Stored Recent records in their original order |
| `idealb50` / `idlb50` | Hypothetical B50 with improved achievement; does not save changes |
| `s50` / `sun50` / `寸50` / `寸止め` | 50 records closest to SSS/SSS+ |

## Filters

```text
b50 -lv 14 14.9 -diff mas rem -scr 100.5
ab50 -ver buddies prism+ -type dx
b50 -dx
b50 -star 5
b50 -page 2 -times 2
```

| Parameter | Behavior |
|---|---|
| `-lv` / `-level` | Level or constant: `14`, `14+`, `14.7`; two values form a range |
| `-ra` / `-rating` | One value matches exact chart Rating; two define an inclusive range |
| `-scr` / `-score` | One value is a minimum achievement; two define an inclusive range |
| `-dx` / `-dxscore` | No value sorts by DX score ratio; one integer percentage is a minimum, two form a range |
| `-star` / `-dxstar` | Exact DX stars or a two-value range |
| `-diff` / `-difficulty` | `bas adv exp mas rem` or full difficulty names; multiple allowed |
| `-type` / `-tp` | `dx`, `std`; multiple allowed |
| `-ver` / `-version` | Exact version names; multiple allowed; use `+` for PLUS, e.g. `buddies prism+` |
| `-next` / `-nxt` | Reclassify old/new charts using the final version in the current dataset; does not predict future constants |
| `-page` / `-pg` | Pages start at 1; old and new groups are paginated separately |
| `-times` / `-tm` | Entry-count multiplier, capped at 2.5 and rounded up to groups of 5; not image scaling |

Selection defaults to descending chart Rating, then achievement. A filter may leave fewer records than the requested count.

`r50` uses stored Recent data. Filters apply, but `-page` and `-times` do not paginate or expand it, and `-dx` does not reorder Recent records.

`sun50` includes only `100.4000%–100.4999%` and `99.9000%–99.9999%`. It sorts by distance to the target, then descending constant, and separates SSS+ and SSS targets.

Ideal mode maps achievement intervals 99–99.5, 99.5–100, 100–100.5, and 100.5–101 to 99.5, 100, 100.5, and 101 respectively. Values below 99 stay unchanged. This is a hypothetical target, not a recorded score.

## Songs, lists, and progress

```text
ヒバナ record
13 records
14.7 records 2
13+ levels
13sss+ prog
14ss+ prog -uc
vocaloid ap prog -up
真極 plate
真極 plate -c
PRiSM PLUS ver
```

`record` searches stored scores by title or alias, with a candidate list for multiple matches. `records` lists personal scores and accepts a page suffix; `levels` lists charts without that page suffix.

`prog` and `levels` accept levels `11`, `11+`, `12`, `12+`, `13`, `13+`, `14`, `14+`, `15`, but not decimal constants. Here `14+` includes level 15. They also accept categories: `vocaloid`, `popani`, `touhou`, `gekichu`, `game`, `maimai`. Targets: `s`, `s+`, `ss`, `ss+`, `sss`, `sss+`, `fc`, `fc+`, `ap`, `ap+`, `fdx`, `fdx+`.

For `prog` and `plate`, append `-uc` for uncleared, `-up` for unplayed, or `-c` for cleared. Plate types are `極`, `将`, `神`, `舞舞`; available versions depend on the server dataset.

## Friends and mentions

```text
friends
friend-rcd <friend_code> b50 -lv 14+
@friend b50
@friend 13 records
@friend 14sss+ prog
```

`friends` / `friend list` and `friend-rcd` require a private chat and full SEGA binding. They fetch friend data from maimai NET. Mentions use a different data source: the target's stored JiETNG records.

Mentions support B-series, `record`, `records`, `prog`, `plate`, and `rank`. The target must be registered, have the required data, and allow mention queries. Invalid targets never fall back to your data. `levels` uses your own account; self-only account actions reject mentions of others.

## Image recognition and judgement analysis

Send a result image, then use LINE's Reply action to quote that image:

- `rec`: recognize and validate the title, achievement, and judgements. Usually returns an analysis image; multiple valid solutions can produce multiple images.
- `rec -flex`: return interactive result cards for inspection and correction.
- `crop`: preview the cropped recognition regions.
- `info`: read the song title from the quoted image and look up the song.

Include the main result and secondary judgement table where possible. Incomplete or inconsistent input may fail or require correction. Recognition does not import the result into Best/Recent.

### Manual corrections

Use the bot's `fix-rcd` correction template: exactly 7 lines. Line 1 is `fix-rcd Song Title`; line 2 is achievement (0–101, up to 4 decimal places). The next five lines are TAP, HOLD, SLIDE, TOUCH, BREAK, each containing five non-negative integers in `CRITICAL PERFECT/PERFECT/GREAT/GOOD/MISS` order, separated by `/`.

Keep line breaks and omit explanatory text. Corrected input must still pass chart-count and achievement validation. It does not overwrite stored play records.

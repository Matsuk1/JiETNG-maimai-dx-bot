---
title: B50 成绩命令
description: JiETNG 舞萌DX 查分器的 B50、Best 50、Recent 50、DX Rating、レート内訳、等级目标和单曲成绩命令说明。
---

# 成绩命令

<img src="/b50_example.png" alt="Best 50" style="max-width: 280px; width: 100%; margin: 24px auto;" />

## B 系列成绩图

| 命令 | 说明 |
|---|---|
| `b50` / `best50` | 旧曲 35 + 新曲 15 |
| `b40` / `best40` | 旧曲 25 + 新曲 15，使用旧版 Rating 计算 |
| `b35` / `best35` | 旧曲 Best 35 |
| `b15` / `best15` | 新曲 Best 15 |
| `ab35` / `allb35` / `ab50` / `allb50` | 不区分新旧曲，取前 35 / 50 |
| `apb50` / `ap50` | AP/AP+ 筛选后取旧曲 35 + 新曲 15 |
| `fdxb50` / `fdx50` | FDX/FDX+ 筛选后取旧曲 35 + 新曲 15 |
| `rct50` / `r50` | 保存的 Recent 记录，保持原顺序 |
| `idealb50` / `idlb50` | 模拟提高达成率后的 B50，不修改成绩 |
| `s50` / `sun50` / `寸50` / `寸止め` | 距离 SSS/SSS+ 最近的 50 条成绩 |

## 筛选参数

```text
b50 -lv 14 14.9 -diff mas rem -scr 100.5
ab50 -ver buddies prism+ -type dx
b50 -dx
b50 -star 5
b50 -page 2 -times 2
```

| 参数 | 说明 |
|---|---|
| `-lv` / `-level` | 等级或定数；如 `14`、`14+`、`14.7`；两个值为范围 |
| `-ra` / `-rating` | 单值精确匹配单谱 Rating；两个值为闭区间 |
| `-scr` / `-score` | 单值为达成率下限；两个值为闭区间 |
| `-dx` / `-dxscore` | 不带值按 DX 分数比例排序；单值为百分比下限；双值为范围，使用整数百分比 |
| `-star` / `-dxstar` | DX 星数，单值精确匹配或双值范围 |
| `-diff` / `-difficulty` | `bas adv exp mas rem` 或完整难度名，可多选 |
| `-type` / `-tp` | `dx`、`std`，可多选 |
| `-ver` / `-version` | 版本名精确匹配，可多选；PLUS 用 `+`，例如 `buddies prism+` |
| `-next` / `-nxt` | 按当前数据集最后一个版本重新划分新旧曲，不预测未来定数 |
| `-page` / `-pg` | 页码从 1 开始；新旧曲分别分页 |
| `-times` / `-tm` | 条目数量倍率，上限 2.5，按 5 条向上取整；不是图片缩放 |

默认按单谱 Rating、达成率降序选取。筛选后数量不足时不会补满。

`r50` 使用保存的 Recent 数据。筛选有效，但当前实现不会通过 `-page`、`-times` 分页或扩容，也不会用 `-dx` 改变 Recent 的原始顺序。

`寸50` 只收录 `100.4000%–100.4999%` 和 `99.9000%–99.9999%`，先按距目标的差值升序，再按定数降序，分成 SSS+ 与 SSS 两组。

理想分数模式把 99–99.5、99.5–100、100–100.5、100.5–101 的成绩分别模拟为 99.5、100、100.5、101；低于 99 不变。这是目标模拟，不是实际成绩。

## 单曲、列表与目标

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

`record` 按曲名或别名 搜索已保存的个人成绩；多个结果时选择候选。`records` 是个人成绩列表，可加页码；`levels` 是谱面列表，不支持这种页码后缀。

`prog` 与 `levels` 仅支持等级 `11`、`11+`、`12`、`12+`、`13`、`13+`、`14`、`14+`、`15`，不支持小数定数；其中 `14+` 包含 15。也支持分类：`vocaloid`、`popani`、`touhou`、`gekichu`、`game`、`maimai`。目标为 `s`、`s+`、`ss`、`ss+`、`sss`、`sss+`、`fc`、`fc+`、`ap`、`ap+`、`fdx`、`fdx+`。

`prog` 和 `plate` 的末尾筛选：`-uc` 未达成、`-up` 未游玩、`-c` 已达成。牌子类型支持 `極`、`将`、`神`、`舞舞`；可用版本取决于对应服务器曲库。

## 查询好友与群成员

```text
friends
friend-rcd <好友代码> b50 -lv 14+
@好友 b50
@好友 13 records
@好友 14sss+ prog
```

`friends` / `friend list` 和 `friend-rcd` 仅限私聊，需要完整 SEGA 绑定，并实时从 maimai NET 获取好友数据。它们与 @ 查询是两种不同入口。

@ 查询使用被提及用户在 JiETNG 保存的数据，支持 B 系列、`record`、`records`、`prog`、`plate`、`rank`。对方必须已注册、有相应数据且允许被查询；目标无效时不会回退到自己的成绩。`levels` 查询本人；账号操作遇到 @ 他人会被拒绝。

## 图片识别与判定分析

先发送成绩图片，再用 LINE 的「回复」引用那张图片：

- `rec`：识别并校验曲名、达成率和判定，通常返回分析图片；存在多个有效解时可能返回多张。
- `rec -flex`：以交互卡片返回识别结果，便于检查和修正。
- `crop`：返回识别区域裁切预览。
- `info`：从引用图片读取曲名并查询歌曲信息。

请尽量包含主屏与副屏判定表。数据不足或无法校验时会提示失败或要求手动修正。这些操作不会把图片成绩写入 Best/Recent。

### 手动修正

按 Bot 给出的修正模板发送 `fix-rcd`：共 7 行，第一行 `fix-rcd 曲名`，第二行达成率（0–101，最多 4 位小数），后五行依次为 TAP、HOLD、SLIDE、TOUCH、BREAK。每行按 `CRITICAL PERFECT/PERFECT/GREAT/GOOD/MISS` 填写 5 个非负整数，用 `/` 分隔。

保留换行，不要把提示文字一起粘贴。修正结果仍需通过谱面物量和达成率校验，且不会改写已保存的游玩记录。

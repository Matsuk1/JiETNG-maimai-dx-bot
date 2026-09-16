---
title: 舞萌DX 成绩查询与筛选
description: JiETNG 支持 maimai B50、定数、等级、DX Rating、达成率、レート内訳和歌曲成绩查询筛选。
---

# 成绩查询与搜索

JiETNG 的查询能力分为三类：成绩图筛选、歌曲搜索、歌曲 ID 查询。

## 成绩图筛选

B 系列命令支持在同一条消息里追加筛选参数：

```text
b50 -lv 14 14.9 -diff mas rem -scr 100.5
ab50 -ver buddies -type dx
ab50 -page 2
ap50 -lv 13.6
```

可筛选字段包括等级/定数、单谱 Rating、达成率、DX 分数、DX 星数、难度、谱面类型、版本和页码。

筛选结果会继续使用成绩图模板渲染，因此适合用来做“某个定数段的 B50”“只看 MAS/Re:MAS”“只看某版本”等图。

## 歌曲搜索

```text
artist Nanahira
designer Jack
bpm 180
bpm 0-120
bpm 120-180
ヒバナ info
random 14+
```

- `artist` 按艺术家名搜索。
- `designer` 按谱面设计师搜索。
- `bpm` 按 BPM 精确值或范围搜索，支持从 `0` 开始的范围，以及 `120-180`、`120~180`、`120 180`。
- `info` 查询歌曲信息。
- 关键词大小写不敏感。

## 歌曲成绩

```text
ヒバナ record
```

`record` 按歌曲名或别名搜索个人成绩。

## 等级列表

```text
13 records
13+ levels
```

- `records` 输出你的成绩列表。
- `levels` 输出支持的等级/分类谱面列表；小数定数请使用 `records` 或 B 系列 `-lv`。

## 数据来源

查询结果来自 JiETNG 当前保存的加工后成绩数据。数据可能来自：

- `maimai update` 从 maimai NET 同步
- 网页书签通过 Import Token 上传
- 第三方工具通过用户 Import Token 上传的加工后成绩 JSON

如果数据没有更新，查询结果也不会自动重新爬取。需要同步时请手动 `maimai update`，或重新使用网页书签上传。

## 选择正确的查询入口

`info`、`artist`、`designer`、`bpm`、`random` 查询曲库，不需要先同步自己的成绩。`record`、`records` 与 B 系列使用已有个人数据。服务按用户的 JP/INTL 设置选择曲库，未设置时通常使用 JP。

`artist Nanahira 2`、`designer Jack 2` 可翻页。BPM 建议用明确的范围分隔符，如 `bpm 120-180 2`；`bpm 180 2` 是 BPM 180 的第 2 页，`bpm 120 180` 则是范围。

歌曲匹配支持曲名和别名；普通搜索的候选上限为 10，关键词过宽时请缩小范围。列表中的歌曲详情/成绩/Calc 按钮可继续查询，不需要手工拼内部按钮命令。

等级可写 `14` 或 `14+`，精确定数用 `14.7`；`-ver` 是版本名匹配，不是任意子串搜索。参数的精确语义见[成绩命令](/zh/commands/record)。

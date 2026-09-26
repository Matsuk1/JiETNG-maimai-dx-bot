---
title: 舞萌DX 查分器命令大全
description: JiETNG 命令大全，包含舞萌DX / maimai B50、查分、レート内訳、牌子目标、歌曲查询、导出和 Import Token。
---

# JiETNG 命令大全

本文档按当前代码中的命令注册表整理。除特别说明外，命令大小写不敏感。

发送 `help` 查看分类目录；支持帮助的命令可追加 `-help`，例如 `b50 -help`。部分需要参数的命令单独发送时也会显示说明。

## 账号与系统

| 命令 | 说明 |
|------|------|
| `bind` | 生成绑定链接，可绑定 SEGA 账号或选择 Import Token 导入模式 |
| `rebind` | 修改已绑定 SEGA 账号的密码、版本、Aime |
| `settings` | 打开设置页，修改偏好并管理 Import Token |
| `profile` / `getme` | 查看账号资料与绑定状态 |
| `unbind` | 解除绑定并删除数据 |
| `maimai update` / `update` | 从 maimai NET 同步成绩 |
| `export json` / `export xml` | 导出加工后的成绩数据 |
| `status` | 显示机器人运行状态 |
| `help` | 显示命令目录 |

`bind`、`rebind`、`settings`、`update`、`export`、`unbind` 仅限操作自己的账号。

## B 系列成绩图

| 命令 | 说明 |
|------|------|
| `b50` / `best50` | Best 35 + Best 15 |
| `b40` / `best40` | 旧版 Rating 结构 |
| `b35` / `best35` | 旧曲 Best 35 |
| `b15` / `best15` | 新曲 Best 15 |
| `ab35` / `allb35` | All Best 35 |
| `ab50` / `allb50` | All Best 50 |
| `apb50` / `ap50` | AP/AP+ Best 50 |
| `fdxb50` / `fdx50` | FDX/FDX+ Best 50 |
| `rct50` / `r50` | Recent 50 |
| `idealb50` / `idlb50` | 理想分数 Best 50 |
| `寸50` / `寸止め` / `s50` / `sun50` | 寸止め 50：100.4000%-100.4999%、99.9000%-99.9999% |

可追加 `-lv`、`-ra`、`-scr`、`-dx`、`-star`、`-diff`、`-ver`、`-type`、`-next` / `-nxt`、`-page`、`-times` 等参数。

## 歌曲与成绩

| 命令格式 | 说明 |
|---------|------|
| `[曲名] record` / `record` | 查询单曲个人成绩；省略曲名时查询空曲名歌曲 |
| `[曲名] info` / `info` | 查询歌曲信息；省略曲名时查询空曲名歌曲 |
| `artist <关键词> [页码]` | 按艺术家搜索 |
| `designer <关键词> [页码]` | 按谱师搜索 |
| `bpm <BPM或范围> [页码]` | 按 BPM 搜索，如 `bpm 180` / `bpm 0-120` / `bpm 120-180` |

## 列表与目标

| 命令格式 | 说明 |
|---------|------|
| `[等级/定数] records [页码]` | 查看等级或定数成绩列表 |
| `[等级/分类] levels` | 查看谱面列表 |
| `[等级][目标] prog` | 查看等级目标达成情况 |

目标支持 `s`、`s+`、`ss`、`ss+`、`sss`、`sss+`、`fc`、`fc+`、`ap`、`ap+`、`fdx`、`fdx+`。

目标和牌子命令支持后缀：

- `-uc`：未达成
- `-up`：未游玩
- `-c`：已达成

## 牌子与版本

| 命令格式 | 说明 |
|---------|------|
| `[版本牌子] plate` | 查看牌子达成情况 |
| `[版本名] ver` | 查看版本歌曲列表 |

## 好友与群聊

| 命令 | 说明 |
|------|------|
| `friend list` / `friends` | 查看 maimai 好友列表 |
| `friend-rcd <好友代码> [B系列命令] [筛选参数]` | 查看好友成绩图 |
| `@用户 b50` | 群聊查询被提及用户成绩 |

@ 查询只支持成绩相关命令。被提及用户不存在或没有成绩数据时，不会回退为发送者数据。

## 工具

| 命令 | 说明 |
|------|------|
| `rc <定数>` | 查看 Rating 对照表 |
| `calc <tap> <hold> <slide> [touch] <break>` | 计算 Note 分数 |
| `random [等级/定数]` | 随机选曲 |
| `rank` / `ranking` | 排行榜 |
| `rank jp` / `rank intl` | 指定服务器排行榜 |
| 发送 LINE 位置 | 查询附近 maimai 机厅，JP 与 INTL 数据源会合并后排序 |

## 识别与使用范围

| 命令 | 说明 |
|---|---|
| `rec` / `rec -flex` | 回复引用成绩图，返回判定分析图片 / 卡片 |
| `crop` | 回复引用图片，查看裁切区域 |
| `info`（引用图片） | 识别曲名后查询歌曲 |
| `fix-rcd 曲名`（多行） | 按修正模板提交判定；详见成绩命令 |
| `refreshmenu` | 静默刷新 LINE 底部菜单 |

`unbind` 打开网页确认，不是发送第二条确认命令。`friends` / `friend-rcd` 仅限私聊并需要 SEGA 绑定。`prog` 也支持歌曲分类。排行榜仅包含参与的 JiETNG 用户；@ 查询还受目标用户设置控制。`levels` 查询本人，账号操作遇到 @ 他人会被拒绝。

完整参数、Recent 的分页限制与图片识别流程见[成绩命令](/zh/commands/record)；皮肤和隐私开关见[基础命令](/zh/commands/basic)。

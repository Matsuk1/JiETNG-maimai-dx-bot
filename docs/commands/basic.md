# 基础命令

基础命令主要用于账号、设置、状态、导出与支持信息。除特别说明外，命令大小写不敏感。

## 账号与设置

### bind

```text
bind
```

发送绑定链接。仅限私聊。

绑定页支持两种模式：

- 绑定 SEGA 账号，用于 `maimai update` 自动同步。
- 使用导入模式，不绑定 SEGA 账号，只通过 Import Token 和网页书签上传成绩。

### rebind

```text
rebind
```

发送换绑链接，可修改 SEGA 密码、服务器版本与 Aime。仅限已绑定完整 SEGA 账号的用户；SEGA ID 不可更换。仅限私聊。

### settings

```text
settings
```

发送设置页链接。可修改语言、时区、背景、显示设置，并管理 Import Token。完整绑定用户与导入模式用户均可使用。仅限私聊。

### profile / getme

```text
profile
getme
```

查看当前账号资料、绑定状态与服务器版本。

### unbind

在 LINE 私聊发送 `unbind`，打开 Bot 返回的解绑网页并确认。链接有效期为 10 分钟；过期后重新发送 `unbind`。确认后删除 JiETNG 用户资料、Best/Recent 成绩、自定义背景及昵称缓存，无法通过 Bot 撤销。

## 数据更新

```text
maimai update
update
```

从 maimai NET 同步最新成绩。该命令需要完整 SEGA 账号绑定，并且只能用于自己的账号。

导入模式用户请使用网页书签上传成绩。

## 数据导出

```text
export json
export xml
成绩导出 json
成績エクスポート xml
```

导出的是 JiETNG 加工后的成绩数据，不是数据库原始记录。内容包括用户资料、服务器版本、Best 记录、Recent 记录以及用于复现成绩图所需的标准化字段。

## 其他

```text
status
rank
rank jp
rank intl
```

- `status`：显示机器人运行状态。
- `rank` / `ranking`：查看 DX Rating 排行榜，可指定 `jp` 或 `intl`。

## 限制

- `bind`、`rebind`、`settings`、`update`、`export`、`unbind` 为 self-only 命令，不会查询被 @ 提及的用户。
- 群聊中如果 @ 不存在或没有 JiETNG 数据的用户，成绩查询不会回退成你的数据。

## 设置页能做什么？

私聊发送 `settings`。链接有效期为 30 分钟，过期后重新获取。

- **语言与时区**：交互支持简体中文、繁体中文、英文、日文。成绩图片文字按服务器版本决定：JP 为日文，INTL 为英文。
- **成绩图皮肤**：选择服务当前提供的皮肤。部分皮肤不使用背景；缺少的模板会回退到默认模板。
- **背景**：开关背景、选择背景、调节模糊和遮罩。最多上传 2 张自定义背景，每张不超过 5 MiB；支持 PNG、JPEG、WebP，HEIC/HEIF 还需要服务端具备解码支持。
- **排行榜与 @ 查询**：可关闭参与全局排行榜，或禁止他人通过 @ 查询你的成绩；未设置时两项默认开启。
- **Import Token**：创建、撤销，以及删除已撤销 Token。明文只显示一次。
- **第三方权限**：查看关联应用并撤销授权，包括创建账号的 owner 关联。

`rank` 统计 JiETNG 中同服且允许参与的用户，并非 SEGA 官方全体玩家榜。`rank jp` / `rank intl` 显示对应服务器前 15 名。

`refreshmenu` 会重新关联适合当前绑定状态的 LINE 底部菜单，成功时不发送额外回复。

## 获取帮助

发送 `help` 打开分类目录；`b50 -help`、`artist -help`、`rec -help` 查看已有帮助的命令。并非所有内部按钮动作都有聊天帮助。账号操作遇到 @ 他人时会被拒绝，不会悄悄改为操作自己。

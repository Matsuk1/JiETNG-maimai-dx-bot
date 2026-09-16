# 常见问题

## 我必须绑定 SEGA ID 吗？

不一定。JiETNG 现在支持两种方式：

- 绑定 SEGA 账号后使用 `maimai update` 自动同步。
- 使用 Import Token 导入模式，通过网页书签上传成绩。

如果你希望 Bot 主动从 maimai NET 同步，仍然需要完整 SEGA 绑定。

## 如何开始？

1. 私聊 Bot 发送 `bind`。
2. 在网页中选择绑定 SEGA 账号，或选择 Import Token 导入模式。
3. SEGA 用户发送 `maimai update`；导入模式用户打开 `settings` 生成 token 后使用[网页书签工具](/zh/bookmarklet)。
4. 发送 `b50`、`rct50`、`ヒバナ record`、`真極 plate` 等命令查看成绩。

## 可以在聊天里输入 SEGA 密码吗？

不可以。JiETNG 不会要求你在 LINE 聊天中发送密码。SEGA 账号只应在绑定网页中填写。

## Import Token 是什么？

Import Token 是用户级上传凭证，用于把网页书签或第三方工具整理好的成绩 JSON 上传到 JiETNG。它不是开发者 Token，也不能访问其他用户数据。

Token 明文只显示一次。撤销后不能继续上传；已撤销 token 可以在设置页删除。

## 书签工具会做什么？

它在官方 maimai 移动站里运行，使用当前浏览器 session 读取资料、Best 与 Recent 记录。生成图片时调用 JiETNG 的图片接口；保存 Import Token 后可以上传加工后的成绩数据。

它不会读取 SEGA 密码。

## 为什么 `b50` 不是最新？

JiETNG 使用服务器中保存的加工后成绩数据。请先确认你已经：

- 发送 `maimai update`
- 或重新使用网页书签上传成绩

只发送查询命令不会自动重新爬取官方成绩。

## `rebind` 能换 SEGA ID 吗？

不能。`rebind` 用于更新密码、版本和 Aime。要换成完全不同的 SEGA ID，请先 `unbind` 后重新 `bind`。

## 可以导出成绩吗？

可以：

```text
export json
export xml
```

导出内容是加工后的用户资料、Best、Recent 与标准化谱面成绩字段，不是数据库原始数据。

## @ 提及别人为什么查不到？

被 @ 的用户必须已经注册 JiETNG 且有成绩数据。当前逻辑不会在目标用户不存在时回退到发送者自己的数据。

## 附近机厅查询的数据来自哪里？

发送 LINE 位置后，JiETNG 会同时查询 JP 与 INTL 两个机厅数据源，合并后按距离筛选最近的一批。

## 删除数据怎么做？

发送：

`unbind` → 打开返回的网页并确认

会删除 JiETNG 保存的用户数据。此操作不可恢复。

## 遇到问题怎么办？

- 查看[命令大全](/zh/commands/)
- 在 GitHub 提交 Issue
- 加入 Discord 反馈

## 我可以隐藏成绩或退出排行榜吗？

可以。在 `settings` 分别关闭允许他人 @ 查询与排行榜参与。两项默认开启。该设置不等同于撤销第三方开发者授权，应用权限需要在设置页另行管理。

## 为什么图片不是我选择的语言，或背景不显示？

Bot 交互语言与成绩图片语言分开：JP 图片为日文，INTL 为英文。选择的皮肤也可能不使用背景。请检查设置中的皮肤、背景开关与背景选择。

## `rec` 可以代替导入吗？

不可以。`rec`、`rec -flex`、`fix-rcd` 用于判定分析，不写入 Best/Recent。保存成绩需要 `maimai update` 或 Import Token 上传。

## 新用户的 Import Token 从哪里来？

导入模式绑定成功页会立即生成一个 Token，明文只显示一次；不必再生成一个才开始使用。丢失时到 `settings` 创建新 Token，并撤销不再需要的旧 Token。书签成绩有标签页缓存，更新方法见[支持与反馈](/zh/more/support)。

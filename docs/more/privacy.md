# 隐私政策

## 概述

JiETNG 是个人维护的 maimai DX 成绩管理工具。本文说明当前项目会收集、保存和处理哪些数据。

## 数据来源

JiETNG 支持两种用户数据来源：

- **SEGA 账号同步**：用户在绑定页面填写 SEGA ID、密码、版本与 Aime，JiETNG 使用这些信息登录 maimai NET 并同步成绩。
- **Import Token 导入**：用户在设置页生成 Import Token，网页书签或第三方工具上传加工后的 `profile`、`best`、`recent` 数据。

## 保存的数据

可能保存的数据包括：

- LINE 用户 ID
- 语言、时区、背景等用户设置
- SEGA ID、SEGA 密码、服务器版本、Aime
- maimai 用户资料、Rating、称号、头像/姓名框等显示信息
- Best、Recent 与单谱成绩数据
- Import Token 的哈希、状态与创建时间
- 开发者 Token、权限请求和授权关系
- 命令使用记录、错误日志与运行状态日志

Import Token 明文只在生成时显示一次，服务器保存哈希。

## 数据用途

数据用于：

- 同步与导入 maimai 成绩
- 生成成绩图、牌子进度、等级列表与排行榜
- 提供设置页、导出、权限管理和开发者 API
- 防止滥用、排查错误和维护服务稳定

## 第三方服务

JiETNG 会与以下服务交互：

- LINE Platform：接收和发送 Bot 消息
- SEGA maimai NET：同步官方成绩数据

网页书签运行在官方 maimai 移动站页面中，但上传到 JiETNG 的是加工后的成绩数据，不包含 SEGA 密码。

## 删除与导出

在 LINE 私聊发送 `unbind`，打开 Bot 返回的解绑网页并确认。链接有效期为 10 分钟；过期后重新发送 `unbind`。确认后删除 JiETNG 用户资料、Best/Recent 成绩、自定义背景及昵称缓存，无法通过 Bot 撤销。

```text
export json
export xml
```

导出的是加工后的成绩数据。解绑不会立即清除历史日志、已生成图片或既有备份中的所有副本；这些数据的保留取决于部署配置。

## 安全说明

- Web 页面通过 HTTPS 访问。
- 当前应用代码将 SEGA 密码写入用户 JSON，未实现字段级加密，不能承诺密码加密存储。不希望服务保存密码时可使用 Import Token 模式。
- Import Token 与开发者 Token 应像密码一样保管。
- 撤销 Token 后，该 Token 不能继续上传或访问对应资源。

## 联系

- GitHub Issues：[github.com/Matsuk1/JiETNG/issues](https://github.com/Matsuk1/JiETNG/issues)
- Discord：[加入服务器](https://discord.gg/NXxFn9T8Xz)

**生效日期**：2026 年 9 月 16 日

## 可见性、网页体验与图片

排行榜参与及允许他人 @ 查询默认开启，可在 `settings` 分别关闭。第三方应用经授权后可访问相关数据，用户可在设置页撤销授权（包括 owner 关联）。

在线体验页把 SEGA ID/密码发送到 JiETNG 后端完成本次登录与制图，不创建持久绑定账号；若勾选记住账号，页面会在本浏览器 `demo_creds` Cookie 保存包含密码的信息，期限 90 天，取消勾选会清除。书签保存的 Import Token 位于官方站点当前浏览器的 localStorage，JP/INTL 的存储相互独立。

OCR 会下载被引用的 LINE 图片并处理识别结果；生成图片可能作为临时文件提供给 LINE。识别本身不会写入个人成绩。用户背景会保存在服务端，运行日志、备份和临时图片的清理周期由部署配置决定。

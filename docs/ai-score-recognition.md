# 成绩图片识别与 AI 权限

在 LINE 中引用成绩图片发送：

- `rec`：本地 OCR 和数据校验。识别或矫正失败不会调用 Codex；矫正失败的 Flex 表格和 `fix-rcd` 复制命令使用原始 OCR 数据。
- `ai-rec`：直接使用 Codex 识别原图，再校验谱面和达成率。
- `rec -flex` / `ai-rec -flex`：使用 Flex 输出结果。

AI 识别沿用现有 Codex 连接配置。普通 OCR API 不调用 Codex。

权限入口位于 `modules/commands/command_access.py`：
`can_use_command(user_id, command_name)` 判断使用权限，
`require_command_access(user_id, command_name)` 在无权限时抛出 `PermissionError`。
图片命令识别入口及通用命令分发器在执行或入队前检查发送者权限；识别模块不承担鉴权。

`COMMAND_ACCESS_POLICIES` 集中登记特殊权限命令，以标准命令名称为键
（通用命令使用 `Command.name`，别名共享同一权限）。未登记的命令保持原有权限行为。
以后添加特殊权限命令只需登记其名称及白名单环境变量，并可将统一判断函数改为查询付费订阅。

目前 `ai-rec` 使用 `JIETNG_AI_REC_ALLOWED_USERS`：未设置时允许有用户身份的请求；
设置后只允许逗号分隔的用户 ID；设为空字符串则全部拒绝。
当前尚未实现计费、扣费或额度管理。

# 成绩图片识别与 AI 权限

在 LINE 中引用成绩图片发送：

- `rec`：本地 OCR 和数据校验。识别或矫正失败不会调用 Codex；矫正失败的 Flex 表格和 `fix-rcd` 复制命令使用原始 OCR 数据。
- `ai-rec`：直接使用 Codex 识别原图，再校验谱面和达成率。
- `rec -flex` / `ai-rec -flex`：使用 Flex 输出结果。

AI 识别沿用现有 Codex 连接配置。普通 OCR API 不调用 Codex。

权限入口位于 `modules/score_recognition/access.py`：
`can_use_ai_recognition(user_id)` 判断使用权限，
`require_ai_recognition_access(user_id)` 在无权限时抛出 `PermissionError`。
命令入队前和实际 AI 识别前都会检查，用户 ID 来自 LINE 事件。

当前免费阶段，未设置 `JIETNG_AI_REC_ALLOWED_USERS` 时允许有用户身份的请求。
设置后只允许逗号分隔的用户 ID；设为空字符串则全部拒绝。
将来可在该权限函数中接入订阅状态、有效期等查询；当前尚未实现计费、扣费或额度管理。

# 模块组织

优先把代码放进已有的业务目录。只服务于一个模块的转换、格式化和组装函数留在使用处，避免新增 `helper`、`utils` 或转发文件。

## 图片：`images/`

| 文件 | 职责 |
| --- | --- |
| `renderer.py` | HTML 模板、素材内嵌、共享 Chromium 渲染线程 |
| `skins.py` | 皮肤注册、模板选择、用户皮肤上下文 |
| `records.py` | 成绩卡、封面、进度、牌子和 OCR 结果图片，包含卡片 HTML 组装 |
| `songs.py` | 歌曲信息、谱面表和版本歌曲列表 |
| `composition.py` | 资料卡、图标、背景、页脚和图片拼接 |
| `cache.py` | 封面及图标下载缓存 |
| `upload.py` | 图片编码、上传和过期清理 |

难度颜色统一来自 `score_rules.py`。模板仍在仓库根目录的 `templates/images/`，图片资源路径没有迁移。

## 成绩识别：`score_recognition/`

- `recognizer.py`：识别入口和 OCR 引擎生命周期。判定验证分为候选谱面枚举、单次行列对齐校验、超额判定修复和结果应用；修复仅修改候选副本。
- `presentation.py`：API 返回值和 Flex 展示数据转换；不加载配置或启动 OCR。
- `results.py`：结果变体和图片错误类型；不依赖模型初始化。
- `ocr.py`、`cropper.py`、`table_model.py`：OCR、图片裁切和表格模型。

HTTP 路由仍在 `api/score_api.py`。通用评分规则和计算继续由 `score_rules.py`、`score_calculator.py` 负责。

完整成绩识别先走本地定位、OCR 和校验。定位/裁切/引擎异常，或校验未通过且没有本地补全候选时，才使用已启用 AI Monitor 的 Codex 登录尝试一次原图识别。Codex OCR 沿用后台诊断的模型配置（`JIETNG_CODEX_MODEL` 或 `ai_monitor.model`）；未指定时两者都使用 Codex 默认模型，不单独覆盖推理强度。Codex OCR 使用独立临时会话，不启用后台 MCP、网页或 shell 工具；结果必须再次通过谱面和达成率校验。未登录、不可用或结果不合格时保留原错误/手动修正流程。仅歌名识别、手动 `fix-rcd` 和裁切预览不触发保底。

歌名搜索、OCR 错字与滚动标题匹配统一放在 `song_matcher.py`，识别入口直接调用，不保留转发包装。

## LINE 消息：`messages/`

- `layout.py`：公共 Flex 布局、颜色、按钮、表头和统计卡片。只有生成帮助文档链接时才读取服务配置。
- `scores.py`：成绩识别详情和候选结果轮播。先准备展示数据，再分别构建表头、判定表、扣分、BREAK 和验证提示，最后组装消息；各阶段直接返回自己的内容，不修改输入结果。
- `service.py`：账户、状态、查询、好友、公告等业务消息，负责需要用户信息的展示。计算结果卡片按 Note 数量、判定扣分、标题和容错行分步构建，单卡与轮播共用同一构建入口。歌曲搜索和分页列表共用歌曲行与列表容器，分页固定每页 15 首。

成绩消息和命令帮助不导入业务消息模块。调用方直接导入所属模块；原 `message_manager.py` 已删除，不保留转发文件。

## 其他目录

- `api/`：HTTP 路由、认证及接口处理。
- `commands/`：命令路由、参数解析和命令帮助。帮助页面构建集中在 `command_help.py`；`fix-rcd` 与其他命令统一由 `command_parsers.py` 解析。
- `monitoring/`：监控、文件访问与诊断工具。

## 更新与验证

迁移没有保留旧路径转发模块。部署时同步新增目录、调用文件和旧文件删除，并重启服务；仅覆盖上传新文件会留下旧模块。

运行 `.venv/bin/python -m pytest -q`。需要验证 Chromium 渲染时加上 `JIETNG_RENDER_TESTS=1`。离线预览和历史对比仍使用 `devtools/image_preview/server.py`、`scripts/preview_image_migration.py`。

### CPU OCR performance comparison

`JIETNG_OCR_ENABLE_MKLDNN=1` enables oneDNN (default: disabled).
`JIETNG_OCR_CPU_THREADS` controls main OCR threads (default: 4).
The table worker inherits both settings unless overridden by
`JIETNG_TABLE_OCR_ENABLE_MKLDNN` / `JIETNG_TABLE_OCR_CPU_THREADS`.
Restart the service after changing these environment variables.

On the server, run a representative set of local photos through all four
oneDNN off/on × 4/8-thread configurations:

```sh
python3 scripts/benchmark_score_ocr.py /path/to/photo1.jpg /path/to/photo2.jpg --runs 3 --output /tmp/ocr-benchmark
```

This uses production OCR and local validation, never Codex. Each configuration
has a fresh process; later iterations show warm performance unless production
memory/request limits reset the engine. Logs include worker startup, field
recognition and reset events. JSON includes parsed results, validation, elapsed
time and post-request parent/child RSS (not peak memory). Compare accuracy as
well as latency; a faster failed recognition is not a successful optimization.
Run during a quiet period: this loads additional models alongside the service.
Production reset thresholds and model choices are unchanged.

The table worker is retained between requests while its RSS is below
`JIETNG_TABLE_OCR_MAX_RSS_MB` (default 2560 MiB). The previous 1536 MiB limit
was below the measured normal footprint and caused repeated cold starts.
It is recycled after 50 requests (`JIETNG_TABLE_OCR_MAX_REQUESTS`) or when
host available memory falls below 512 MiB (`JIETNG_TABLE_OCR_MIN_AVAILABLE_MB`).
Memory checks happen after inference; these are recycling policies, not hard
peak-memory limits. Explicit environment settings override the defaults.
Keep oneDNN disabled on the tested server: its table pipeline failed with
`ReduceMeanCheckIfOneDNNSupport`. Confirm `reused=True` and near-zero startup
in subsequent table request logs after deploying this change.

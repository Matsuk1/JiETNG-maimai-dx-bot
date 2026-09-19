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


## 空闲内存回收

服务启动时预热主 OCR、表格 OCR、两套 YOLO 和 Playwright。YOLO 执行一次空白图片推理，Playwright 在自己的渲染线程执行一次微型截图，使模型预测器、浏览器和页面在接收业务任务前就绪。

以下组件默认空闲 300 秒后回收，并立即重建已加载的组件，无需等待下一次请求。重建完成后重新计时；启动失败、未加载的组件由后续请求按需重试。设置对应环境变量为 `0` 可关闭空闲回收；修改后重启服务生效。

| 环境变量 | 回收内容 |
| --- | --- |
| `JIETNG_TABLE_OCR_IDLE_SECONDS` | 终止并等待独立表格 OCR 子进程退出、关闭通信管道，立即启动新模型进程 |
| `JIETNG_OCR_IDLE_SECONDS` | 释放主 OCR 引擎引用、执行垃圾回收并立即重建 |
| `JIETNG_CROPPER_IDLE_SECONDS` | 释放已加载的 YOLO 裁切模型引用、执行垃圾回收并立即重新加载，包含裁切预览使用的模型 |
| `JIETNG_RENDERER_IDLE_SECONDS` | 在渲染线程内关闭 Chromium 和 Playwright、清空 Base64 素材缓存并立即重建浏览器与页面 |

OCR/YOLO 由现有 120 秒周期清理触发，因此通常在空闲 300–420 秒后回收；模型锁被占用时跳过。Playwright 在渲染队列等待超时后自行回收，正在执行的渲染不会中断。识别或渲染失败也会更新空闲计时。渲染线程等待期间不保留上一次任务的 HTML 和截图 Future。

表格 OCR 的现有 RSS、请求次数及系统可用内存保护仍然生效。主 OCR/YOLO 的 Python 引用释放不保证底层推理库立即归还全部 RSS；独立 OCR 与浏览器进程退出会释放其进程资源。重建期间到达的请求会等待对应组件锁或渲染队列；重建失败会记录日志，并由后续请求重试。重建会恢复模型和浏览器的基础内存占用。

## OCR 检测尺寸与日志

文字检测默认将长边限制为 1280 像素，避免判定表先放大 3 倍、列图再放大 5 倍后，以最高 4000 像素运行检测。PaddleOCR 仍使用传入的原图裁出文字供识别，坐标也返回原图坐标。

可在服务环境中设置 `JIETNG_OCR_DET_MAX_SIDE`（整数，至少 32），重启服务生效。默认 `1280`；如特定图片出现漏检，可设为 `4000` 对比。这个选项控制普通文字和列补识别的检测器，不修改独立表格模型。

常规 INFO 日志包含：

- `Score OCR timing`：裁切、曲名、达成率、判定表分别耗时。判定表耗时包括必要的列/单元格补识别，不含请求排队、模型首次加载和后续成绩校验。
- `Table OCR request`：是否复用表格模型、加载和推理耗时、内存、完整/部分结果模式。
- `OCR lock wait`：等待共享 OCR 锁超过 1 秒时记录，区分排队与计算。

比较优化前后时，使用相同图片、相同服务器配置，先预热模型，再串行重复请求。比较判定数字和最终成绩校验结果，不能只看耗时。不要并行运行两组模型基准，以免 CPU 和内存争用干扰结果。

## 日志约定

使用模块级 logger 和 `[模块]` 标识。INFO 记录请求阶段、耗时和结果；
DEBUG 记录详细诊断；WARNING 记录重试和降级；ERROR 记录最终失败，
需要堆栈时使用 `logger.exception`。使用参数格式化（如
`logger.info("elapsed=%.3fs", elapsed)`），避免提前拼接被过滤的日志。
不输出密码、认证 token 或完整认证页面。

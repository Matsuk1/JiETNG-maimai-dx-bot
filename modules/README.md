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

- `recognizer.py`：识别入口、歌曲匹配、判定验证和 OCR 引擎生命周期。
- `presentation.py`：API 返回值和 Flex 展示数据转换；不加载配置或启动 OCR。
- `results.py`：结果变体和图片错误类型；不依赖模型初始化。
- `ocr.py`、`cropper.py`、`table_model.py`：OCR、图片裁切和表格模型。

HTTP 路由仍在 `api/score_api.py`。通用评分规则和计算继续由 `score_rules.py`、`score_calculator.py` 负责。

## 其他目录

- `api/`：HTTP 路由、认证及接口处理。
- `commands/`：命令路由、参数解析和命令帮助。
- `monitoring/`：监控、文件访问与诊断工具。

## 更新与验证

迁移没有保留旧路径转发模块。部署时同步新增目录、调用文件和旧文件删除，并重启服务；仅覆盖上传新文件会留下旧模块。

运行 `.venv/bin/python -m pytest -q`。需要验证 Chromium 渲染时加上 `JIETNG_RENDER_TESTS=1`。离线预览和历史对比仍使用 `devtools/image_preview/server.py`、`scripts/preview_image_migration.py`。

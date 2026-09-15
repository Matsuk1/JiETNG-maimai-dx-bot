# 图片渲染

面向用户的成绩、封面、单曲、牌子、等级进度、版本列表、识别结果、资料卡、公共背景页脚、404 占位图和后台 PWA 图标均通过 HTML/CSS + Playwright Chromium 生成。

## 部署

安装项目依赖后，使用运行服务的 Python 环境安装对应的浏览器：

```sh
python -m playwright install chromium
# Linux / Docker 同时安装系统依赖：
python -m playwright install --with-deps chromium
```

如果设置 `PLAYWRIGHT_BROWSERS_PATH`，安装与运行服务必须使用相同的值。浏览器与 Python Playwright 版本需要匹配。模板位于 `templates/images/`，必须随应用部署。

## 实现

- `modules/html_renderer.py`：每进程一个专用工作线程，最多接纳 8 个渲染任务；复用 Chromium 页面与字体；进程退出关闭浏览器，fork 后重新初始化。模板转义外部文本，素材嵌入 data URI，截图页不访问网络。
- `modules/html_cards.py`：复用封面和成绩卡片 HTML；成绩列表、版本列表与单曲成绩整页渲染。素材下载继续使用现有缓存。外部传入的进度封面仍保持 Pillow 图片接口。
- `modules/profile_generator.py`：保持现有头像和资料素材下载逻辑。LINE 头像选择仍在 `main.py`。固定字体行高匹配原资料卡的文字基线。
- `modules/image_manager.py`：公共背景、模糊、拼接与页脚。`compose_images` 不关闭输入；`compose_generated_images` 在成功或失败后释放输入。

返回值仍为 Pillow 图像，上传、编码、压缩和 OCR 裁切/增强接口保持兼容。OCR 调试图和菜单点击区域诊断工具继续使用图像处理代码。

## 验证和对比

```sh
JIETNG_RENDER_TESTS=1 python -m pytest -q
python scripts/preview_image_migration.py --output artifacts/image-migration/before --ref f75636b^
python scripts/preview_image_migration.py --output artifacts/image-migration/after
python scripts/compare_image_migration.py artifacts/image-migration
```

样例只使用公开歌曲和合成成绩，图标读取本地缓存。完整资料卡样例使用 `data/images/keep_nameplate.png`，并从 `--profile-assets` 指定的目录读取 `class.png`、`course.png`、`trophy.png`；默认目录为 `artifacts/image-migration/profile-assets`。这些对比产物不提交到 Git。

生产运行需要先安装 Chromium；首次启动耗时、内存占用和字体抗锯齿与 Pillow 不同。新模板根据内容自动计算部分图片高度，因此前后高度可能略有差异。

## 实时调试页面

运行 `.venv/bin/python -m devtools.image_preview.server`，打开 <http://127.0.0.1:5088>。
提供 12 套固定 JSON 示例、快捷字段、自动渲染、模板保存监听、缩放与 PNG 下载。
具体说明见 [本地图片调试台](devtools/image_preview/README.md)。

## 成绩图皮肤

`generate_records_picture(..., skin="default")`、`create_thumbnail(..., skin="default")`
和 `create_thumbnail_in_line(..., skin="default")` 支持显式选择皮肤。
组合生成器通过请求隔离的 ContextVar 向嵌套模板传递皮肤；旧调用无需修改。
作用域退出（包括异常）会恢复原选择，截图队列只接收已展开的 HTML。

皮肤目录为 `templates/images/skins/<id>/`，包含 `skin.json`（例如
`{"label": "皮肤名称"}`）和要覆盖的同名图片模板。
未知皮肤或缺少的模板自动回退到原有模板。模板数据与成绩计算共用，
默认模板继续放在 `templates/images/`。新皮肤使用自己的 CSS 类名前缀，
避免影响组合图片中的其他组件。小卡片保持 300×150，横向卡片保持 600×225，
成绩列表宽度保持 1580；列表高度由内容决定。

调试台可切换皮肤并记住浏览器选择，递归监听皮肤模板修改。
成绩列表、卡片、封面、单曲、资料、进度、版本、识别结果和合成页脚均已接入。
后台图标和 404 占位图不参与皮肤切换。聊天命令及用户数据库的皮肤偏好尚未接入，
业务生成器可以传入 `skin`；组合调用也可用 `with use_skin("ios-glass"):`。
`document.html`（浏览器基础字体和画布）与 `stack.html`（图片堆叠）
是共享结构，不另复制皮肤版本，堆叠中的图片会继承当前皮肤。

内置 `ios-glass` 皮肤提供浅蓝紫渐变、半透明面板、高光边框，以及成绩列表、
小卡片、横向卡片及其余图片场景的玻璃样式。难度用卡片及封面的彩色外框表示。示例：

```python
generate_records_picture(up_songs, down_songs, title="B50", skin="ios-glass")
```

部署此皮肤时，一并上传 `modules/image_skins.py` 和
`templates/images/skins/ios-glass/`（包含 `skin.json`）。

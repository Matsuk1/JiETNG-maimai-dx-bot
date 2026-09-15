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

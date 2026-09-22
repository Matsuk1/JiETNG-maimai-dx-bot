---
title: 网页书签工具
description: JiETNG maimai DX 网页书签工具，使用当前 maimai 官方网站登录状态生成 B50 / AP50 图片，并可手动上传加工后成绩。
---

# JiETNG 网页书签工具

这个书签工具会在 maimai DX 官方网站中运行，使用当前浏览器登录状态读取资料、Best 记录与 Recent 记录，然后调用 JiETNG API 生成 B50 / AP50 图片。它不会读取或要求输入 SEGA ID 密码。

<div class="bookmarklet-installer">
  <div class="bookmarklet-card">
    <img src="/logo.svg" alt="JiETNG" class="bookmarklet-logo">
    <div>
      <p class="bookmarklet-eyebrow">Bookmarklet</p>
      <h2>JiETNG 工具包</h2>
      <p>把下面的按钮拖到浏览器书签栏。之后在 maimai 官方页面登录后点击它，就会在当前页面弹出成绩图。</p>
    </div>
    <a id="jietng-bookmarklet-link" class="bookmarklet-button" href="#">JiETNG 工具包</a>
    <button id="jietng-copy-bookmarklet" class="bookmarklet-copy" type="button">复制书签地址</button>
    <p id="jietng-copy-status" class="bookmarklet-status"></p>
  </div>
</div>

## 使用方法

1. 把上面的 **JiETNG 工具包** 按钮拖到浏览器书签栏。
2. 打开并登录日服或国际服 maimai DX 官方网站：
   - `https://maimaidx.jp/maimai-mobile/home/`
   - `https://maimaidx-eng.com/maimai-mobile/home/`
3. 在官方页面点击刚才保存的书签。
4. 可选填写 `settings` 页面生成的 Import Token。保存后会保留在当前浏览器，需要上传成绩时点击 **Upload**。
5. 选择 **B50** 或 **AP50**，然后点击 **Generate**。
6. 等待生成完成，在页面弹窗中查看图片。图片生成超过 15 秒会提示超时，可刷新后重试。

## 当前行为

- 支持日服与国际服官方域名，会自动识别 `jp` / `intl`。
- 成绩图直接显示在官方页面上，不跳转到 JiETNG 站点，也不会强制下载。
- 预览区在书签主面板上方，生成后提供下载与关闭按钮。
- 刷新官方页面后再次打开书签，浮层会保留在页面上，但不会立刻显示旧缓存图片。
- 点击 Generate 只生成图片，不上传成绩；需要上传时可使用 Upload 按钮。
- 上传内容是加工后的 `profile`、`best`、`recent` 数据，服务端不会接收 SEGA 密码。

## Import Token

Import Token 在 LINE 私聊发送 `settings` 后进入设置页生成。明文只显示一次，请保存在当前浏览器或自行妥善保存。

设置页可以：

- 创建新的 Import Token
- 撤销正在使用的 Token
- 删除已撤销 Token

导入模式账号会在第一次上传成绩时初始化资料与成绩数据。

如果你的浏览器不方便拖拽按钮，可以点击 **复制书签地址**，然后手动新建书签，把 URL 设置为复制出来的 `javascript:...` 内容。

## 缓存、Token 与图片格式

Generate 不需要 Token；Upload 需要用户 Import Token。导入模式注册成功页已生成首个 Token，也可以从 `settings` 新建。

Token 保存在当前官方站点的 localStorage，JP 与 INTL 独立。资料和成绩还会保存在当前标签页的 sessionStorage，刷新页面不一定重新采集。需要最新数据或切换 Aime 时，关闭旧标签页并在新标签页重新登录、运行书签。清除浏览器内的 Token 不等于撤销服务端凭证，停用 Token 请到设置页撤销。

图片接口实际返回 JPEG。当前书签下载逻辑可能仍使用 `.png` 文件名，若软件提示格式不符，可改名为 `.jpg`。Generate 会把制图所需的资料和 Best 数据发送给 JiETNG，但不会保存到账号；Upload 才会写入账号的 profile、Best 和 Recent。

<script setup>
import { onMounted } from 'vue'

onMounted(async () => {
  const link = document.getElementById('jietng-bookmarklet-link')
  const copyButton = document.getElementById('jietng-copy-bookmarklet')
  const status = document.getElementById('jietng-copy-status')
  let bookmarklet = ''

  try {
    const response = await fetch('/bookmarklet/maimai-session-image.txt', { cache: 'no-store' })
    bookmarklet = (await response.text()).trim()
    link.href = bookmarklet
  } catch (error) {
    status.textContent = '书签脚本加载失败，请稍后重试。'
    copyButton.disabled = true
  }

  copyButton.addEventListener('click', async () => {
    if (!bookmarklet) return
    try {
      await navigator.clipboard.writeText(bookmarklet)
      status.textContent = '已复制。现在可以手动新建书签并粘贴到 URL。'
    } catch (error) {
      status.textContent = '复制失败，请尝试拖拽按钮到书签栏。'
    }
  })
})
</script>

<style>
.bookmarklet-installer {
  margin: 28px 0 32px;
}

.bookmarklet-card {
  position: relative;
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 14px 18px;
  align-items: center;
  overflow: hidden;
  padding: 22px;
  border: 1px solid color-mix(in srgb, var(--vp-c-brand-1) 18%, var(--vp-c-divider));
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(37, 99, 235, .08), rgba(255, 255, 255, .92));
  box-shadow:
    0 18px 46px rgba(15, 23, 42, .12),
    inset 0 1px 0 rgba(255, 255, 255, .45);
}

.bookmarklet-logo {
  position: relative;
  width: 72px;
  height: 72px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, .70);
  border-radius: 18px;
  background: rgba(255, 255, 255, .76);
  box-shadow: 0 10px 24px rgba(37, 99, 235, .14);
}

.bookmarklet-eyebrow {
  margin: 0 0 4px;
  color: var(--vp-c-brand-1);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.bookmarklet-card h2 {
  margin: 0 0 6px;
  border: 0 !important;
  border-bottom: 0 !important;
  padding: 0;
  color: var(--vp-c-text-1) !important;
  font-size: 24px;
  line-height: 1.25;
  text-decoration: none !important;
  box-shadow: none !important;
}

.bookmarklet-card p {
  margin: 0;
  color: var(--vp-c-text-2);
}

.bookmarklet-button,
.bookmarklet-copy {
  display: inline-flex;
  grid-column: 2;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 42px;
  padding: 0 18px;
  border-radius: 11px;
  transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease, background .16s ease;
  font-weight: 700;
  border-bottom: 0 !important;
  text-decoration: none !important;
}

.bookmarklet-button {
  margin-top: 6px;
  color: #fff !important;
  background: linear-gradient(135deg, #2563eb, #0891b2);
  box-shadow: 0 10px 22px rgba(37, 99, 235, .26);
}

.bookmarklet-button:hover,
.bookmarklet-copy:hover {
  transform: translateY(-1px);
}

.bookmarklet-button:hover {
  color: #fff !important;
  box-shadow: 0 14px 28px rgba(37, 99, 235, .32);
  text-decoration: none !important;
}

.bookmarklet-button::before {
  content: "";
  width: 18px;
  height: 18px;
  margin-right: 8px;
  background: url('/logo.svg') center / contain no-repeat;
  filter: drop-shadow(0 1px 1px rgba(0,0,0,.18));
}

.bookmarklet-copy {
  border: 1px solid var(--vp-c-divider);
  color: var(--vp-c-text-1);
  background: color-mix(in srgb, var(--vp-c-bg) 88%, white);
  cursor: pointer;
}

.bookmarklet-copy:hover {
  border-color: color-mix(in srgb, var(--vp-c-brand-1) 35%, var(--vp-c-divider));
}

.bookmarklet-copy:disabled {
  cursor: not-allowed;
  opacity: .58;
  transform: none;
}

.bookmarklet-status {
  grid-column: 2;
  min-height: 20px;
  color: var(--vp-c-text-2);
  font-size: 13px;
}

html.dark .bookmarklet-card,
.dark .bookmarklet-card {
  background: linear-gradient(135deg, rgba(37, 99, 235, .20), rgba(30, 41, 59, .92));
  box-shadow:
    0 18px 46px rgba(0, 0, 0, .30),
    inset 0 1px 0 rgba(255, 255, 255, .08);
}

html.dark .bookmarklet-logo,
.dark .bookmarklet-logo {
  border-color: rgba(255, 255, 255, .12);
  background: rgba(255, 255, 255, .08);
}

html.dark .bookmarklet-copy,
.dark .bookmarklet-copy {
  background: rgba(255, 255, 255, .06);
}

@media (max-width: 640px) {
  .bookmarklet-card {
    grid-template-columns: 1fr;
    padding: 20px;
  }

  .bookmarklet-logo {
    width: 64px;
    height: 64px;
  }

  .bookmarklet-button,
  .bookmarklet-copy,
  .bookmarklet-status {
    grid-column: 1;
    width: 100%;
  }
}
</style>

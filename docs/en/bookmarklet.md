---
title: Bookmarklet Tool
description: JiETNG maimai DX bookmarklet that uses the current official maimai session to generate B50 / AP50 images and manually upload processed records.
---

# JiETNG Bookmarklet Tool

This bookmarklet runs on the official maimai DX mobile website. It uses your current browser session to read your profile, Best records, and Recent records, then calls the JiETNG API to generate a B50 / AP50 image. It never reads or asks for your SEGA ID password.

<div class="bookmarklet-installer">
  <div class="bookmarklet-card">
    <img src="/logo.png" alt="JiETNG" class="bookmarklet-logo">
    <div>
      <p class="bookmarklet-eyebrow">Bookmarklet</p>
      <h2>JiETNG Toolkit</h2>
      <p>Drag the button below to your bookmarks bar. After logging in on the official maimai site, click it to open the generated score image on the same page.</p>
    </div>
    <a id="jietng-bookmarklet-link" class="bookmarklet-button" href="#">JiETNG Toolkit</a>
    <button id="jietng-copy-bookmarklet" class="bookmarklet-copy" type="button">Copy bookmark URL</button>
    <p id="jietng-copy-status" class="bookmarklet-status"></p>
  </div>
</div>

## How to Use

1. Drag the **JiETNG Toolkit** button above to your bookmarks bar.
2. Open and log in to one of the official maimai DX sites:
   - `https://maimaidx.jp/maimai-mobile/home/`
   - `https://maimaidx-eng.com/maimai-mobile/home/`
3. Click the saved bookmark while staying on the official page.
4. Optionally enter the Import Token generated from the `settings` page. After saving it, the bookmarklet keeps it in this browser. Click **Upload** when you want to upload records.
5. Select **B50** or **AP50**, then click **Generate**.
6. Wait for generation to finish, then view the image in the page overlay. If image generation takes more than 15 seconds, the bookmarklet shows a timeout message and asks you to refresh and retry.

## Current Behavior

- Supports JP and INTL official domains and detects `jp` / `intl` automatically.
- Shows the image directly on the official page. It does not redirect to JiETNG and does not force a download.
- The preview panel appears above the main bookmarklet panel, with Download and Close actions after generation.
- Reopening after refresh keeps the overlay, but does not immediately show the old cached image.
- Generate only creates an image and never uploads records. Use the Upload button when you want to upload.
- Uploads contain processed `profile`, `best`, and `recent` data, never the SEGA password.

## Import Token

Send `settings` to the LINE bot and create an Import Token in the settings page. The plaintext token is shown only once.

The settings page can create tokens, revoke active tokens, and delete revoked tokens.

If dragging is inconvenient in your browser, click **Copy bookmark URL**, create a bookmark manually, and paste the copied `javascript:...` content into the URL field.

## Cache, tokens, and image format

Generate needs no token; Upload requires a user Import Token. Import-only setup already creates the first token; `settings` can create more.

Tokens are stored in localStorage on the official site, separately for JP and INTL. Profile/records are also cached in the tab's sessionStorage, so reloading may reuse old data. For new scores or a different Aime, close the old tab and log in/run the bookmarklet in a new tab. Clearing a token from the browser does not revoke it on the server; revoke it in settings.

The image endpoint returns JPEG. The current bookmarklet may still download it with a `.png` filename; rename it to `.jpg` if an application reports a format mismatch. Generate sends profile/Best data to JiETNG for rendering without storing account records; Upload writes profile, Best, and Recent to the account.

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
    status.textContent = 'Failed to load the bookmarklet. Please try again later.'
    copyButton.disabled = true
  }

  copyButton.addEventListener('click', async () => {
    if (!bookmarklet) return
    try {
      await navigator.clipboard.writeText(bookmarklet)
      status.textContent = 'Copied. You can now create a bookmark manually and paste it as the URL.'
    } catch (error) {
      status.textContent = 'Copy failed. Try dragging the button to your bookmarks bar.'
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
  background: url('/logo.png') center / contain no-repeat;
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

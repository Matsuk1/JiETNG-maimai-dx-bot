---
title: ブックマークレットツール
description: maimai 公式サイトの現在のログイン状態を使って B50 / AP50 画像生成と加工済み成績の手動アップロードを行う JiETNG ブックマークレット。
---

# JiETNG ブックマークレットツール

このブックマークレットは maimai DX 公式モバイルサイト上で動作します。現在のブラウザのログイン状態を使ってプロフィール、Best レコード、Recent レコードを読み取り、JiETNG API で B50 / AP50 画像を生成します。SEGA ID のパスワードを読み取ったり入力させたりすることはありません。

<div class="bookmarklet-installer">
  <div class="bookmarklet-card">
    <img src="/logo.svg" alt="JiETNG" class="bookmarklet-logo">
    <div>
      <p class="bookmarklet-eyebrow">Bookmarklet</p>
      <h2>JiETNG ツールキット</h2>
      <p>下のボタンをブラウザのブックマークバーへドラッグしてください。maimai 公式サイトにログインした後、そのブックマークをクリックすると同じページ上にスコア画像が表示されます。</p>
    </div>
    <a id="jietng-bookmarklet-link" class="bookmarklet-button" href="#">JiETNG ツールキット</a>
    <button id="jietng-copy-bookmarklet" class="bookmarklet-copy" type="button">ブックマークURLをコピー</button>
    <p id="jietng-copy-status" class="bookmarklet-status"></p>
  </div>
</div>

## 使い方

1. 上の **JiETNG ツールキット** ボタンをブックマークバーへドラッグします。
2. 公式 maimai DX サイトを開いてログインします。
   - `https://maimaidx.jp/maimai-mobile/home/`
   - `https://maimaidx-eng.com/maimai-mobile/home/`
3. 公式ページ上で保存したブックマークをクリックします。
4. 必要に応じて `settings` ページで生成した Import Token を入力します。保存すると、このブラウザに保持されます。成績をアップロードしたい場合は **Upload** を押します。
5. **B50** または **AP50** を選び、**Generate** を押します。
6. 生成が完了すると、ページ内のオーバーレイで画像を確認できます。画像生成が 15 秒を超えた場合はタイムアウトを表示し、更新して再試行するよう案内します。

## 現在の動作

- 国内版と海外版の公式ドメインに対応し、`jp` / `intl` を自動判定します。
- 画像は公式ページ上に直接表示されます。JiETNG 側へ遷移せず、強制ダウンロードもしません。
- プレビューはメインパネルより上に表示され、生成後に Download と Close を表示します。
- 更新後に再度開くとオーバーレイは保持されますが、古いキャッシュ画像を即表示しません。
- Generate は画像生成のみを行い、成績をアップロードしません。必要なときは Upload ボタンを使います。
- アップロード内容は加工済みの `profile`、`best`、`recent` データで、SEGA パスワードは含みません。

## Import Token

LINE Bot に `settings` を送信し、設定ページで Import Token を作成します。平文 token は一度だけ表示されます。

設定ページでは token の作成、撤回、撤回済み token の削除ができます。

ドラッグ操作が使いにくい場合は、**ブックマークURLをコピー** を押して手動でブックマークを作成し、URL 欄にコピーした `javascript:...` を貼り付けてください。

## キャッシュ・Token・画像形式

Generate は Token 不要、Upload はユーザー Import Token が必要です。取り込み専用登録時に最初の Token が作成され、`settings` で追加作成できます。

Token は公式サイトの localStorage に保存され、JP/INTL で独立しています。プロフィール・成績はタブの sessionStorage にも保存されるため、再読み込みでも古いデータを再利用する場合があります。最新成績や別 Aime では古いタブを閉じ、新しいタブでログイン・実行してください。ブラウザから Token を消すだけでは失効しません。設定から撤回してください。

画像 API は JPEG を返します。現ブックマークレットは `.png` 名で保存する場合があるため、形式エラーなら `.jpg` に変更してください。Generate は描画用プロフィール・Best を JiETNG に送りますがアカウント記録を保存しません。Upload が profile・Best・Recent を書き込みます。

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
    status.textContent = 'ブックマークレットの読み込みに失敗しました。しばらくしてから再試行してください。'
    copyButton.disabled = true
  }

  copyButton.addEventListener('click', async () => {
    if (!bookmarklet) return
    try {
      await navigator.clipboard.writeText(bookmarklet)
      status.textContent = 'コピーしました。手動でブックマークを作成し、URL として貼り付けてください。'
    } catch (error) {
      status.textContent = 'コピーに失敗しました。ボタンをブックマークバーへドラッグしてください。'
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

<script setup lang="ts">
import { computed } from 'vue'
import { useData, withBase } from 'vitepress'

const { lang } = useData()
const locale = computed(() => lang.value.startsWith('zh') ? 'zh' : lang.value.startsWith('en') ? 'en' : 'ja')
const prefix = computed(() => locale.value === 'ja' ? '' : `/${locale.value}`)
const copy = computed(() => ({
  zh: {
    eyebrow: '你的下一次进步，从这里开始', title: '从一首歌，到你的 Best 50。',
    intro: '在 LINE 中管理 maimai DX 成绩。支持日服 JP 与国际服 INTL，随时查看 B50、Recent 50 和 DX Rating。',
    preview: 'B50 成绩图示例', heading: '三步开始使用',
    steps: [ ['添加好友', '添加 JiETNG，在 LINE 私聊中发送 bind。'], ['同步成绩', '绑定 SEGA 账号后发送 maimai update，或使用 Import Token 与网页书签导入。'], ['查看你的 B50', '发送 b50 生成成绩图，使用 record、定数筛选或牌子命令继续探索。'] ],
    guide: '阅读入门指南', resources: '继续探索', commands: '命令参考', bookmarklet: '网页书签工具', api: '开发者 API', support: '问题与支持'
  },
  en: {
    eyebrow: 'MAKE YOUR NEXT PLAY COUNT', title: 'From one song to your Best 50.',
    intro: 'Track your maimai DX scores in LINE. View B50, Recent 50, and DX Rating for both JP and INTL servers.',
    preview: 'Example B50 score card', heading: 'Get started in three steps',
    steps: [ ['Add a friend', 'Add JiETNG on LINE and send bind in a private chat.'], ['Sync your scores', 'Bind your SEGA account and send maimai update, or import with an Import Token and the bookmarklet.'], ['See your Best 50', 'Send b50 to generate a score card, then explore record filters and plate progress.'] ],
    guide: 'Read the getting started guide', resources: 'Keep exploring', commands: 'Command reference', bookmarklet: 'Bookmarklet', api: 'Developer API', support: 'Help and support'
  },
  ja: {
    eyebrow: '次のプレイを、次の一歩に', title: '一曲の記録から、Best 50 へ。',
    intro: 'LINE で maimai DX のスコアを管理。国内版 JP・海外版 INTL の B50、Recent 50、DX Rating をいつでも確認できます。',
    preview: 'B50 スコア画像のサンプル', heading: '3 ステップではじめよう',
    steps: [ ['友だち追加', 'JiETNG を LINE に追加し、個別チャットで bind を送信。'], ['スコアを同期', 'SEGA 連携後に maimai update を送信。または Import Token とブックマークレットで取り込み。'], ['Best 50 を確認', 'b50 でスコア画像を作成。record、定数検索、プレート進捗も確認できます。'] ],
    guide: 'クイックスタートを読む', resources: 'もっと使いこなす', commands: 'コマンド一覧', bookmarklet: 'ブックマークレット', api: '開発者 API', support: 'サポート'
  }
}[locale.value]))
</script>

<template>
  <div class="home-content">
    <section class="score-showcase" aria-labelledby="score-heading">
      <div>
        <p class="eyebrow">{{ copy.eyebrow }}</p>
        <h2 id="score-heading">{{ copy.title }}</h2>
        <p>{{ copy.intro }}</p>
      </div>
      <figure>
        <a :href="withBase('/b50_example.png')" target="_blank" rel="noopener noreferrer">
          <img :src="withBase('/b50_example.png')" :alt="copy.preview" loading="lazy" width="1680" height="2406">
        </a>
        <figcaption>{{ copy.preview }}</figcaption>
      </figure>
    </section>
    <section class="home-start" aria-labelledby="start-heading">
      <h2 id="start-heading">{{ copy.heading }}</h2>
      <ol class="start-steps">
        <li v-for="(step, index) in copy.steps" :key="index">
          <span class="step-number" aria-hidden="true">0{{ index + 1 }}</span>
          <h3>{{ step[0] }}</h3><p>{{ step[1] }}</p>
        </li>
      </ol>
      <a class="guide-link" :href="withBase(`${prefix}/guide/getting-started`)">{{ copy.guide }} →</a>
    </section>
    <nav class="home-resources" :aria-label="copy.resources">
      <h2>{{ copy.resources }}</h2>
      <div>
        <a :href="withBase(`${prefix}/commands/`)">{{ copy.commands }} →</a>
        <a :href="withBase(`${prefix}/bookmarklet`)">{{ copy.bookmarklet }} →</a>
        <a :href="withBase(`${prefix}/developer-api`)">{{ copy.api }} →</a>
        <a :href="withBase(`${prefix}/more/support`)">{{ copy.support }} →</a>
      </div>
    </nav>
  </div>
</template>

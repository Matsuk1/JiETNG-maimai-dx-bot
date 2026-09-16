// .vitepress/theme/index.ts
import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import { h } from 'vue'
import GoogleTranslate from './GoogleTranslate.vue'
import LanguageRedirect from './LanguageRedirect.vue'
import LineFriendButton from './LineFriendButton.vue'
import HomeContent from './HomeContent.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('LineFriendButton', LineFriendButton)
    app.component('HomeContent', HomeContent)
  },
  Layout() {
    return h(DefaultTheme.Layout, null, {
      'layout-top': () => h(LanguageRedirect),
      'sidebar-nav-after': () => h('div', { class: 'sidebar-line-action' }, h(LineFriendButton)),
      'nav-bar-content-after': () => h(GoogleTranslate)
    })
  }
} satisfies Theme

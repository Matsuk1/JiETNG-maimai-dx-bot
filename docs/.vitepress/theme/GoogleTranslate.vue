<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useData, useRoute } from 'vitepress'

type TranslateElementConstructor = new (
  options: Record<string, unknown>,
  element: string
) => void

declare global {
  interface Window {
    googleTranslateElementInit?: () => void
    google?: {
      translate?: {
        TranslateElement?: TranslateElementConstructor
      }
    }
  }
}

const { lang } = useData()
const route = useRoute()
const target = ref<string | null>(null)
const state = ref<'loading' | 'ready' | 'error'>('loading')
let observer: MutationObserver | undefined
let loadTimer: ReturnType<typeof setTimeout> | undefined
let disposed = false
let initialized = false

const copy = computed(() => {
  if (lang.value.startsWith('ja')) return {
    more: 'その他の言語', loading: '翻訳を読み込み中…',
    unavailable: '翻訳を読み込めませんでした。', fallback: 'Google Translate で開く'
  }
  if (lang.value.startsWith('en')) return {
    more: 'More languages', loading: 'Loading translation…',
    unavailable: 'Translation unavailable', fallback: 'Open in Google Translate'
  }
  return {
    more: '更多语言', loading: '正在加载翻译…',
    unavailable: '翻译服务加载失败。', fallback: '用 Google 翻译打开'
  }
})

const fallbackUrl = computed(() => {
  // Google's proxy cannot fetch localhost; use the corresponding published page.
  const origin = typeof window === 'undefined' || ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)
    ? 'https://jietng.matsuk1.com' : window.location.origin
  return `https://translate.google.com/translate?sl=auto&tl=en&u=${encodeURIComponent(origin + route.path)}`
})

function updateTarget() {
  // Match VitePress's mobile, extra-menu, and desktop language breakpoints.
  const selector = window.innerWidth < 768
    ? '.VPNavScreenTranslations .list'
    : window.innerWidth < 1280
      ? '.VPNavBarExtra .translations'
      : '.VPNavBarTranslations .items'
  target.value = document.querySelector(selector) ? selector : null
  if (document.querySelector('#google_translate_control .goog-te-combo')) {
    state.value = 'ready'
    clearTimeout(loadTimer)
  }
}

function initialize() {
  if (disposed || initialized) return
  const TranslateElement = window.google?.translate?.TranslateElement
  if (!TranslateElement) return
  initialized = true
  try {
    new TranslateElement({
      pageLanguage: lang.value.startsWith('zh') ? 'zh-CN' : lang.value.startsWith('en') ? 'en' : 'ja',
      includedLanguages: 'ja,en,zh-CN,zh-TW,ko,fr,de,es,th,vi,id',
      autoDisplay: false
    }, 'google_translate_control')
    updateTarget()
  } catch {
    state.value = 'error'
  }
}

onMounted(async () => {
  await nextTick()
  if (disposed) return
  updateTarget()
  observer = new MutationObserver(updateTarget)
  observer.observe(document.body, { childList: true, subtree: true })
  window.addEventListener('resize', updateTarget)
  loadTimer = setTimeout(() => {
    if (state.value !== 'ready') state.value = 'error'
  }, 12000)

  if (window.google?.translate?.TranslateElement) {
    initialize()
    return
  }
  window.googleTranslateElementInit = initialize
  const existing = document.getElementById('google-translate-script')
  if (!existing) {
    const script = document.createElement('script')
    script.id = 'google-translate-script'
    script.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit'
    script.async = true
    script.onerror = () => { if (!disposed) state.value = 'error' }
    document.head.appendChild(script)
  }
})

// The widget binds to its initial source language and translated DOM. A native
// locale change needs a fresh document, rather than another widget instance.
watch(lang, () => {
  if (initialized && !disposed) window.location.reload()
})

onBeforeUnmount(() => {
  disposed = true
  observer?.disconnect()
  clearTimeout(loadTimer)
  window.removeEventListener('resize', updateTarget)
  if (window.googleTranslateElementInit === initialize) delete window.googleTranslateElementInit
})
</script>

<template>
  <!-- Keep one persistent host even while the mobile menu is not mounted.
       Teleport moves the initialized widget instead of constructing duplicates. -->
  <div hidden>
    <Teleport :to="target || 'body'" :disabled="!target">
      <li class="google-translate-menu google-translate-entry notranslate">
        <p class="google-translate-title">{{ copy.more }}</p>
        <div id="google_translate_control" class="google-translate-control" />
        <p v-if="state !== 'ready'" class="google-translate-status" role="status">
          {{ state === 'loading' ? copy.loading : copy.unavailable }}
        </p>
        <a v-if="state === 'error'" class="google-translate-fallback"
          :href="fallbackUrl" target="_blank" rel="noopener noreferrer">{{ copy.fallback }}</a>
      </li>
    </Teleport>
  </div>
</template>

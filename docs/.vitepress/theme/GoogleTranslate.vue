<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useData, useRoute } from 'vitepress'

const { lang } = useData()
const route = useRoute()
const target = ref<string | null>(null)
let observer: MutationObserver | undefined

const title = computed(() => {
  if (lang.value.startsWith('ja')) return 'その他の言語'
  if (lang.value.startsWith('en')) return 'More languages'
  return '更多语言'
})

const prompt = computed(() => {
  if (lang.value.startsWith('ja')) return '翻訳する言語を選択'
  if (lang.value.startsWith('en')) return 'Choose a language'
  return '选择翻译语言'
})

function updateTarget() {
  const selector = window.innerWidth < 768
    ? '.VPNavScreenTranslations .list'
    : window.innerWidth < 1280
      ? '.VPNavBarExtra .translations'
      : '.VPNavBarTranslations .items'
  target.value = document.querySelector(selector) ? selector : null
}

function translate(event: Event) {
  const select = event.currentTarget as HTMLSelectElement
  if (!select.value) return
  const url = new URL('https://translate.google.com/translate')
  url.searchParams.set('sl', 'auto')
  url.searchParams.set('tl', select.value)
  url.searchParams.set('u', `https://jietng.matsuk1.com${route.path}`)
  window.open(url, '_blank', 'noopener,noreferrer')
  select.value = ''
}

onMounted(async () => {
  await nextTick()
  updateTarget()
  observer = new MutationObserver(updateTarget)
  observer.observe(document.body, { childList: true, subtree: true })
  window.addEventListener('resize', updateTarget)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  window.removeEventListener('resize', updateTarget)
})
</script>

<template>
  <div hidden>
    <Teleport :to="target || 'body'" :disabled="!target">
      <li class="google-translate-menu google-translate-entry notranslate">
        <p class="google-translate-title">{{ title }}</p>
        <select class="google-translate-select" :aria-label="prompt" @change="translate">
          <option value="">{{ prompt }}</option>
          <option value="zh-TW">繁體中文</option>
          <option value="ko">한국어</option>
          <option value="fr">Français</option>
          <option value="de">Deutsch</option>
          <option value="es">Español</option>
          <option value="th">ไทย</option>
          <option value="vi">Tiếng Việt</option>
          <option value="id">Bahasa Indonesia</option>
        </select>
      </li>
    </Teleport>
  </div>
</template>

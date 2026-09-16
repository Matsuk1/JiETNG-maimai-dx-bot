<script setup lang="ts">
import { computed } from 'vue'
import { useData } from 'vitepress'

const { lang } = useData()
const label = computed(() => lang.value.startsWith('zh')
  ? '添加 LINE 好友'
  : lang.value.startsWith('en') ? 'Add friend on LINE' : 'LINE で友だち追加')
</script>

<template>
  <a class="line-friend-button" href="https://lin.ee/Q6O7aI8" target="_blank" rel="noopener noreferrer">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M20 10.5c0 4.1-4.4 7.6-10.5 10l.8-4C6 16 3 13.7 3 10.5 3 6.9 6.8 4 11.5 4S20 6.9 20 10.5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
      <path d="M8 10.5h7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
    </svg>
    {{ label }}
    <span aria-hidden="true">↗</span>
  </a>
</template>

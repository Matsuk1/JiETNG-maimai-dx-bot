// .vitepress/theme/index.ts
import DefaultTheme from 'vitepress/theme'
import { onMounted, watch, nextTick } from 'vue'
import { useRoute } from 'vitepress'
import type { Theme } from 'vitepress'

export default {
  extends: DefaultTheme,
  setup() {
    const route = useRoute()

    const initMermaid = async () => {
      if (typeof window !== 'undefined') {
        try {
          const mermaid = (await import('mermaid')).default
          mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            themeVariables: {
              primaryColor: '#ff1744',
              primaryTextColor: '#fff',
              primaryBorderColor: '#ff1744',
              lineColor: '#666',
              secondaryColor: '#006400',
              tertiaryColor: '#fff'
            }
          })

          // 查找所有 mermaid 代码块并渲染
          await nextTick()
          const mermaidElements = document.querySelectorAll('.language-mermaid')
          mermaidElements.forEach((element, index) => {
            const code = element.textContent || ''
            const container = document.createElement('div')
            container.className = 'mermaid'
            container.textContent = code
            element.parentElement?.replaceChild(container, element)
          })

          mermaid.run()
        } catch (error) {
          console.error('Failed to load mermaid:', error)
        }
      }
    }

    onMounted(() => {
      initMermaid()
    })

    watch(
      () => route.path,
      () => nextTick(() => initMermaid())
    )
  }
} satisfies Theme

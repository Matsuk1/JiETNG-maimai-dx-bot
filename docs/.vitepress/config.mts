import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

// https://vitepress.dev/reference/site-config
export default withMermaid(defineConfig({
  title: "JiETNG",
  description: "Maimai DX Score Management Bot",
  titleTemplate: ":title | JiETNG - Maimai DX LINE-Bot for JP & Intl Servers",

  cleanUrls: true,

  // 排除文件
  srcExclude: ['**/README.md'],

  // Base URL配置
  // GitHub Pages (username.github.io/JiETNG/): 使用 '/JiETNG/'
  // 自定义域名 (docs.jietng.com): 使用 '/'
  base: '/',

  // Sitemap 配置（用于 SEO）
  sitemap: {
    hostname: 'https://jietng.matsuki.work'
  },

  // Markdown 配置
  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark'
    }
  },

  // 主题配置
  themeConfig: {
    logo: '/logo.svg',

    // 导航栏
    nav: [
      { text: '首页', link: '/' },
      { text: '指南', link: '/guide/getting-started' },
      { text: '功能', link: '/features/search' },
      { text: '命令', link: '/commands/basic' }
    ],

    // 侧边栏
    sidebar: [
      {
        text: '开始使用',
        items: [
          { text: '介绍', link: '/guide/introduction' },
          { text: '快速开始', link: '/guide/getting-started' },
          { text: '绑定账号', link: '/guide/binding' }
        ]
      },
      {
        text: '命令参考',
        items: [
          { text: '基础命令', link: '/commands/basic' },
          { text: '成绩命令', link: '/commands/record' }
        ]
      },
      {
        text: '功能特性',
        items: [
          { text: '成绩查询', link: '/features/search' },
          { text: '好友系统', link: '/features/friends' }
        ]
      },
      {
        text: '更多',
        items: [
          { text: '常见问题', link: '/more/faq' },
          { text: '隐私政策', link: '/more/privacy' },
          { text: '支持', link: '/more/support' },
          { text: '许可证', link: '/more/license' }
        ]
      }
    ],

    // 社交链接
    socialLinks: [
      { icon: 'github', link: 'https://github.com/Matsuk1/JiETNG' }
    ],

    // 页脚
    footer: {
      message: 'Released under the Proprietary License.',
      copyright: 'Copyright © 2025 Matsuki. All Rights Reserved.'
    },

    // 搜索
    search: {
      provider: 'local'
    },

    // 编辑链接
    editLink: {
      pattern: 'https://github.com/Matsuk1/JiETNG/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页'
    },

    // 最后更新时间
    lastUpdated: {
      text: '最后更新',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'short'
      }
    }
  },

  // 多语言支持
  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      description: 'JiETNG - 支持日服和国际服的 maimai DX 查分机器人。追踪进度，分析表现，与好友竞争。免费的 Rating 计算器和 Best 50 图表生成器。'
    },
    en: {
      label: 'English',
      lang: 'en',
      link: '/en/',
      description: 'JiETNG - Maimai DX score management bot for LINE supporting both Japanese and International servers. Track your progress, analyze performance, and compete with friends.',
      themeConfig: {
        nav: [
          { text: 'Home', link: '/en/' },
          { text: 'Guide', link: '/en/guide/getting-started' },
          { text: 'Features', link: '/en/features/search' },
          { text: 'Commands', link: '/en/commands/basic' }
        ],
        sidebar: [
          {
            text: 'Getting Started',
            items: [
              { text: 'Introduction', link: '/en/guide/introduction' },
              { text: 'Quick Start', link: '/en/guide/getting-started' },
              { text: 'Binding Account', link: '/en/guide/binding' }
            ]
          },
          {
            text: 'Commands',
            items: [
              { text: 'Basic Commands', link: '/en/commands/basic' },
              { text: 'Record Commands', link: '/en/commands/record' }
            ]
          },
          {
            text: 'Features',
            items: [
              { text: 'Score Search', link: '/en/features/search' },
              { text: 'Friend System', link: '/en/features/friends' }
            ]
          },
          {
            text: 'More',
            items: [
              { text: 'FAQ', link: '/en/more/faq' },
              { text: 'Privacy', link: '/en/more/privacy' },
              { text: 'Support', link: '/en/more/support' },
              { text: 'License', link: '/en/more/license' }
            ]
          }
        ],
        editLink: {
          pattern: 'https://github.com/Matsuk1/JiETNG/edit/main/docs/:path',
          text: 'Edit this page on GitHub'
        },
        lastUpdated: {
          text: 'Updated at',
          formatOptions: {
            dateStyle: 'short',
            timeStyle: 'short'
          }
        }
      }
    },
    ja: {
      label: '日本語',
      lang: 'ja',
      link: '/ja/',
      description: 'JiETNG - 国内版と海外版の両方に対応した maimai でらっくす スコア管理ボット。無料のレーティング計算機とベスト50チャート生成器。',
      themeConfig: {
        nav: [
          { text: 'ホーム', link: '/ja/' },
          { text: 'ガイド', link: '/ja/guide/getting-started' },
          { text: '機能', link: '/ja/features/search' },
          { text: 'コマンド', link: '/ja/commands/basic' }
        ],
        sidebar: [
          {
            text: '始めに',
            items: [
              { text: '紹介', link: '/ja/guide/introduction' },
              { text: 'クイックスタート', link: '/ja/guide/getting-started' },
              { text: 'アカウント連携', link: '/ja/guide/binding' }
            ]
          },
          {
            text: 'コマンド',
            items: [
              { text: '基本コマンド', link: '/ja/commands/basic' },
              { text: 'レコードコマンド', link: '/ja/commands/record' }
            ]
          },
          {
            text: '機能',
            items: [
              { text: '楽曲検索', link: '/ja/features/search' },
              { text: 'フレンド機能', link: '/ja/features/friends' }
            ]
          },
          {
            text: 'その他',
            items: [
              { text: 'よくある質問', link: '/ja/more/faq' },
              { text: 'プライバシー', link: '/ja/more/privacy' },
              { text: 'サポート', link: '/ja/more/support' },
              { text: 'ライセンス', link: '/ja/more/license' }
            ]
          }
        ],
        editLink: {
          pattern: 'https://github.com/Matsuk1/JiETNG/edit/main/docs/:path',
          text: 'GitHub でこのページを編集'
        },
        lastUpdated: {
          text: '最終更新',
          formatOptions: {
            dateStyle: 'short',
            timeStyle: 'short'
          }
        }
      }
    }
  },

  // 头部meta标签
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' }],
    ['link', { rel: 'icon', type: 'image/png', href: '/favicon.ico' }],
    ['link', { rel: 'apple-touch-icon', href: '/logo.svg' }],
    ['meta', { name: 'theme-color', content: '#2563eb' }],

    // Google Search Console 验证
    ['meta', { name: 'google-site-verification', content: 'AFFp6ZYIkyQJr6lPnfQ5iQt_eLXph0pjhIgbYqsr7eU' }],

    // SEO meta标签
    ['meta', { name: 'keywords', content: 'maimai, maimai DX, maimai でらっくす, maimaiでらっくす, maimai bot, score tracker, rating calculator, best 50, b50, LINE bot, 舞萌DX, 舞萌, 成绩管理, 查分器, スコア管理, レーティング計算, maimaiDXボット, ベスト50, 日本サーバー, 国際サーバー, 日本版, 海外版, 日版, 国际版, maimaiDX bot, rhythm game, arcade game tracker, Japanese server, International server, 日服, 国际服' }],
    ['meta', { name: 'description', content: 'JiETNG - Maimai DX score management bot for LINE supporting both Japanese and International servers. Track your progress, analyze performance, and compete with friends. Free rating calculator and best 50 chart generator.' }],
    ['meta', { name: 'author', content: 'Matsuki' }],

    // Open Graph
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'JiETNG' }],
    ['meta', { property: 'og:title', content: 'JiETNG - Maimai DX Score Management Bot' }],
    ['meta', { property: 'og:description', content: 'Maimai DX score management bot supporting both Japanese and International servers. Track your progress, analyze performance, and compete with friends.' }],
    ['meta', { property: 'og:image', content: 'https://jietng.matsuki.work/logo.svg' }],
    ['meta', { property: 'og:url', content: 'https://jietng.matsuki.work' }],

    // Twitter Card
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:title', content: 'JiETNG - Maimai DX Score Management Bot' }],
    ['meta', { name: 'twitter:description', content: 'Maimai DX score management bot supporting both Japanese and International servers. Track your progress, analyze performance, and compete with friends.' }],
    ['meta', { name: 'twitter:image', content: 'https://jietng.matsuki.work/logo.svg' }]
  ],

  // Mermaid 配置
  mermaid: {
    // 参考 https://mermaid.js.org/config/setup/modules/mermaidAPI.html#mermaidapi-configuration-defaults
  }
}))

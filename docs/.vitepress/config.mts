import { defineConfig } from 'vitepress'
import { withMermaid } from 'vitepress-plugin-mermaid'

const siteUrl = 'https://jietng.matsuk1.com'
const siteDescription = 'JiETNG は国内版 JP と海外版 INTL に対応した maimai でらっくす スコア管理 Bot。B50、Best 50、Recent 50、DX Rating、レート内訳、ブックマークレット取り込みに対応。'

// https://vitepress.dev/reference/site-config
export default withMermaid(defineConfig({
  title: "JiETNG",
  description: siteDescription,
  titleTemplate: ':title | JiETNG · maimai B50 / レート内訳',

  cleanUrls: true,

  // 排除文件
  srcExclude: ['**/README.md'],

  // 日文をルートに、簡体字中国語を /zh/ に配置する。
  rewrites: (id) => {
    if (id.startsWith('ja/')) return id.slice(3)
    if (id.startsWith('en/')) return id
    return `zh/${id}`
  },

  // Base URL配置
  // GitHub Pages (username.github.io/JiETNG/): 使用 '/JiETNG/'
  // 自定义域名 (docs.jietng.com): 使用 '/'
  base: '/',

  // Sitemap 配置（用于 SEO）
  sitemap: {
    hostname: siteUrl
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

    // ナビゲーション
    nav: [
      { text: 'ホーム', link: '/' },
      { text: 'ガイド', link: '/guide/getting-started' },
      { text: '機能', link: '/features/search' },
      { text: 'コマンド', link: '/commands/basic' },
      { text: 'ブックマークレット', link: '/bookmarklet' }
    ],

    // サイドバー
    sidebar: [
      {
        text: '始めに',
        items: [
          { text: 'クイックスタート', link: '/guide/getting-started' },
          { text: '体験する', link: '/demo' },
          { text: 'ブックマークレット', link: '/bookmarklet' }
        ]
      },
      {
        text: 'コマンド',
        items: [
          { text: 'コマンド一覧', link: '/commands/' },
          { text: '基本コマンド', link: '/commands/basic' },
          { text: 'レコードコマンド', link: '/commands/record' }
        ]
      },
      {
        text: '機能',
        items: [
          { text: '楽曲検索', link: '/features/search' }
        ]
      },
      {
        text: 'その他',
        items: [
          { text: 'よくある質問', link: '/more/faq' },
          { text: 'プライバシー', link: '/more/privacy' },
          { text: 'サポート', link: '/more/support' },
          { text: 'ライセンス', link: '/more/license' },
          { text: '開発者 API', link: '/developer-api' }
        ]
      }
    ],

    // フッター
    footer: {
      message: 'すべてのプレイを記録に残そう',
      copyright: 'Copyright © 2025 Matsuki. All Rights Reserved.'
    },

    // 搜索
    search: {
      provider: 'local'
    },

    // 最后更新时间
    lastUpdated: {
      text: '最終更新',
      formatOptions: {
        dateStyle: 'short',
        timeStyle: 'short'
      }
    }
  },

  // 多言語対応
  locales: {
    root: {
      label: '日本語',
      lang: 'ja',
      description: siteDescription
    },
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      link: '/zh/',
      description: '舞萌DX 查分器 — JiETNG 支持日服 JP 与国际服 INTL，提供 maimai B50、Best 50、Recent 50、DX Rating、レート内訳、牌子进度和网页书签导入。',
      themeConfig: {
        nav: [
          { text: '首页', link: '/zh/' },
          { text: '指南', link: '/zh/guide/getting-started' },
          { text: '功能', link: '/zh/features/search' },
          { text: '命令', link: '/zh/commands/basic' },
          { text: '网页书签', link: '/zh/bookmarklet' }
        ],
        sidebar: [
          {
            text: '开始使用',
            items: [
              { text: '快速开始', link: '/zh/guide/getting-started' },
              { text: '在线体验', link: '/zh/demo' },
              { text: '网页书签工具', link: '/zh/bookmarklet' }
            ]
          },
          {
            text: '命令参考',
            items: [
              { text: '命令大全', link: '/zh/commands/' },
              { text: '基础命令', link: '/zh/commands/basic' },
              { text: '成绩命令', link: '/zh/commands/record' }
            ]
          },
          {
            text: '功能特性',
            items: [
              { text: '成绩查询', link: '/zh/features/search' }
            ]
          },
          {
            text: '更多',
            items: [
              { text: '常见问题', link: '/zh/more/faq' },
              { text: '隐私政策', link: '/zh/more/privacy' },
              { text: '支持', link: '/zh/more/support' },
              { text: '许可证', link: '/zh/more/license' },
              { text: '开发者 API', link: '/zh/developer-api' }
            ]
          }
        ],
        lastUpdated: {
          text: '最后更新',
          formatOptions: {
            dateStyle: 'short',
            timeStyle: 'short'
          }
        },
        footer: {
          message: '让每一次游玩都有迹可循',
          copyright: 'Copyright © 2025 Matsuki. 保留所有权利。'
        }
      }
    },
    en: {
      label: 'English',
      lang: 'en',
      link: '/en/',
      description: 'JiETNG is a maimai DX score tracker and LINE bot for JP and INTL servers, with B50, Best 50, Recent 50, DX Rating, rate breakdown, and bookmarklet import.',
      themeConfig: {
        nav: [
          { text: 'Home', link: '/en/' },
          { text: 'Guide', link: '/en/guide/getting-started' },
          { text: 'Features', link: '/en/features/search' },
          { text: 'Commands', link: '/en/commands/basic' },
          { text: 'Bookmarklet', link: '/en/bookmarklet' }
        ],
        sidebar: [
          {
            text: 'Getting Started',
            items: [
              { text: 'Quick Start', link: '/en/guide/getting-started' },
              { text: 'Try It Online', link: '/en/demo' },
              { text: 'Bookmarklet Tool', link: '/en/bookmarklet' }
            ]
          },
          {
            text: 'Commands',
            items: [
              { text: 'Complete Reference', link: '/en/commands/' },
              { text: 'Basic Commands', link: '/en/commands/basic' },
              { text: 'Record Commands', link: '/en/commands/record' }
            ]
          },
          {
            text: 'Features',
            items: [
              { text: 'Score Search', link: '/en/features/search' }
            ]
          },
          {
            text: 'More',
            items: [
              { text: 'FAQ', link: '/en/more/faq' },
              { text: 'Privacy', link: '/en/more/privacy' },
              { text: 'Support', link: '/en/more/support' },
              { text: 'License', link: '/en/more/license' },
              { text: 'Developer API', link: '/en/developer-api' }
            ]
          }
        ],
        lastUpdated: {
          text: 'Updated at',
          formatOptions: {
            dateStyle: 'short',
            timeStyle: 'short'
          }
        },
        footer: {
          message: 'Making every play count',
          copyright: 'Copyright © 2025 Matsuki. All Rights Reserved.'
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
    ['meta', { name: 'application-name', content: 'JiETNG' }],
    ['meta', { name: 'apple-mobile-web-app-title', content: 'JiETNG' }],
    ['meta', { name: 'robots', content: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1' }],
    ['meta', { name: 'googlebot', content: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1' }],

    // 站长验证（中文搜索引擎；申请到 token 后填进 content）
    ['meta', { name: 'google-site-verification', content: '7wQ3HIU-rk6iSNe441mvYPgkZwuotIB3PlOx6r3xOm8' }],
    // ['meta', { name: 'baidu-site-verification', content: 'codeva-XXXXXXXX' }],   // https://ziyuan.baidu.com/
    // ['meta', { name: 'msvalidate.01',           content: 'XXXXXXXXXXXXXXXX' }],   // https://www.bing.com/webmasters
    // ['meta', { name: '360-site-verification',   content: 'XXXXXXXXXXXXXXXX' }],
    // ['meta', { name: 'sogou_site_verification', content: 'XXXXXXXXXXXXXXXX' }],

    // SEO meta 标签（含中/日/英三语长尾，覆盖典型搜索词）
    ['meta', { name: 'keywords', content: [
      // 核心 - 中文（最常搜）
      '舞萌DX查分器', '舞萌查分器', 'maimai查分器', 'maimai 查分', 'maimai dx 查分器',
      '舞萌 b50', '舞萌 B50', '舞萌DX B50', '舞萌 成绩图', '舞萌成绩图', '舞萌 rating',
      '舞萌DX rating', '舞萌DX レート', '舞萌DX レート内訳',
      '舞萌DX', '舞萌', '舞萌dx', 'maimaiDX bot',
      '舞萌国服', '舞萌日服', '舞萌国际服', 'maimai 日服', 'maimai 国际服', '日版', '国际版', '日服', '国际服',
      '舞萌成绩', 'B50 查分', 'b50', 'best 50', 'rating 计算', 'Rating 查询', '牌子进度', '极将神舞舞', '段位查询',
      // 核心 - 日文
      'maimai でらっくす', 'maimai DX', 'maimaiでらっくす', 'スコア管理', 'スコア管理ボット', 'レーティング計算',
      'レート内訳', 'maimai レート内訳', 'maimai B50', 'maimai b50', 'でらっくすRATING', 'DX Rating',
      'ベスト50', 'ベストスコア', 'maimaiDXボット', '日本サーバー', '国際サーバー', '海外版',
      // 核心 - 英文
      'maimai', 'maimai bot', 'maimai dx score tracker', 'score tracker', 'rating calculator',
      'maimai b50', 'maimai best 50', 'maimai rating breakdown', 'maimai DX Rating',
      'best 50 generator', 'LINE bot', 'rhythm game', 'arcade game tracker',
      'Japanese server', 'International server', 'JP server', 'INTL server',
      // 项目名
      'JiETNG', 'JiETNG bot',
    ].join(', ') }],
    ['meta', { name: 'description', content: siteDescription }],
    ['meta', { name: 'author', content: 'Matsuki' }],

    // Open Graph
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'JiETNG' }],
    ['meta', { property: 'og:title', content: 'JiETNG · maimai B50 / レート内訳' }],
    ['meta', { property: 'og:description', content: siteDescription }],
    ['meta', { property: 'og:image', content: `${siteUrl}/og-image.png` }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { property: 'og:image:type', content: 'image/png' }],
    ['meta', { property: 'og:url', content: siteUrl }],
    ['meta', { property: 'og:locale', content: 'ja_JP' }],
    ['meta', { property: 'og:locale:alternate', content: 'zh_CN' }],
    ['meta', { property: 'og:locale:alternate', content: 'en_US' }],

    // Twitter Card
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:title', content: 'JiETNG · maimai B50 / レート内訳' }],
    ['meta', { name: 'twitter:description', content: siteDescription }],
    ['meta', { name: 'twitter:image', content: `${siteUrl}/og-image.png` }],

    // hreflang for main locale entry points
    ['link', { rel: 'alternate', hreflang: 'ja', href: `${siteUrl}/` }],
    ['link', { rel: 'alternate', hreflang: 'zh-CN', href: `${siteUrl}/zh/` }],
    ['link', { rel: 'alternate', hreflang: 'en', href: `${siteUrl}/en/` }],
    ['link', { rel: 'alternate', hreflang: 'x-default', href: `${siteUrl}/` }],

    // JSON-LD 结构化数据（让 Google 知道这是个 WebApplication，不是普通博客）
    ['script', { type: 'application/ld+json' }, JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebApplication',
      'name': 'JiETNG',
      'alternateName': ['舞萌DX 查分器', '舞萌查分器', 'maimai DX Score Tracker', 'maimai B50', 'maimai レート内訳', 'maimai でらっくす スコア管理ボット'],
      'url': siteUrl,
      'description': siteDescription,
      'applicationCategory': 'GameApplication',
      'operatingSystem': 'Any (LINE)',
      'inLanguage': ['ja', 'zh-CN', 'en'],
      'keywords': '舞萌DX查分器, 舞萌查分器, maimai B50, maimai レート内訳, DX Rating, Best 50, Recent 50',
      'offers': {
        '@type': 'Offer',
        'price': '0',
        'priceCurrency': 'JPY'
      },
      'author': {
        '@type': 'Person',
        'name': 'Matsuki',
        'url': 'https://github.com/Matsuk1'
      }
    }) ],

    ['script', { type: 'application/ld+json' }, JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      'name': 'JiETNG',
      'alternateName': ['舞萌DX 查分器', 'maimai DX Score Tracker', 'maimai レート内訳'],
      'url': siteUrl,
      'inLanguage': ['ja', 'zh-CN', 'en']
    }) ]
  ],

  // Mermaid 配置
  mermaid: {
    // 参考 https://mermaid.js.org/config/setup/modules/mermaidAPI.html#mermaidapi-configuration-defaults
  }
}))

# JiETNG Documentation Setup Guide

This guide will help you get the JiETNG documentation website up and running.

## What's Been Created

I've set up a complete VitePress documentation website for JiETNG with:

### ✨ Features

- 🎨 **Beautiful Design**: Modern gradient theme (pink-purple-red)
- 🌐 **Multi-Language**: English, Japanese (日本語), Chinese (中文)
- 🌙 **Dark Mode**: Full dark theme support
- 📱 **Responsive**: Perfect on mobile, tablet, and desktop
- 🔍 **Search**: Built-in full-text search
- ⚡ **Fast**: Optimized with Vite
- 🎭 **Animations**: Smooth hover effects and transitions

### 📁 Structure

```
docs/
├── .vitepress/
│   ├── config.mts              # Site configuration (multi-lang)
│   └── theme/
│       ├── index.ts            # Theme setup
│       └── style.css           # Custom gradients & styles
├── guide/
│   ├── introduction.md         # Project introduction
│   └── getting-started.md      # Quick start guide
├── features/
│   └── b50.md                  # Best 50 documentation
├── commands/
│   └── basic.md                # Command reference
├── more/
│   ├── license.md              # License information
│   └── support.md              # Support & contact
├── index.md                    # Homepage with hero section
├── package.json                # Dependencies
├── README.md                   # Documentation about docs
├── DEPLOY.md                   # Deployment guide
└── SETUP_GUIDE.md             # This file
```

## Quick Start

### 1. Install Node.js

Make sure you have Node.js 18+ installed:

```bash
node --version  # Should be v18 or higher
```

If not installed: [Download Node.js](https://nodejs.org/)

### 2. Install Dependencies

```bash
cd /Users/matsuki/Desktop/JiETNG/docs
npm install
```

This will install VitePress and dependencies (~30 seconds).

### 3. Start Development Server

```bash
npm run docs:dev
```

Visit: **http://localhost:5173**

You should see the beautiful homepage with gradient hero section!

### 4. Build for Production

```bash
npm run docs:build
```

Output: `.vitepress/dist/`

### 5. Preview Production Build

```bash
npm run docs:preview
```

## Next Steps

### 📝 Add More Content

Create new pages:

```bash
# Example: Create FAQ page
touch docs/more/faq.md
```

Then add it to `.vitepress/config.mts` sidebar.

### 🌍 Add Translations

Create Japanese/Chinese versions:

```bash
# Japanese version
mkdir -p docs/ja/guide
cp docs/guide/introduction.md docs/ja/guide/introduction.md
# Edit and translate

# Chinese version
mkdir -p docs/zh/guide
cp docs/guide/introduction.md docs/zh/guide/introduction.md
# Edit and translate
```

### 🎨 Customize

Edit `.vitepress/theme/style.css` to change:
- Colors (gradients, accent colors)
- Fonts
- Spacing
- Animations

Edit `.vitepress/config.mts` to change:
- Navigation
- Sidebar structure
- Site title
- Footer
- Social links

### 🚀 Deploy

See `DEPLOY.md` for detailed deployment instructions.

**Quick deploy to GitHub Pages:**

```bash
npm run docs:build
cd .vitepress/dist
git init
git add -A
git commit -m 'Deploy docs'
git push -f git@github.com:Matsuk1/JiETNG.git main:gh-pages
```

Then enable GitHub Pages in repository settings.

## Customization Guide

### Change Colors

Edit `.vitepress/theme/style.css`:

```css
:root {
  /* Brand colors - change these! */
  --vp-c-brand-1: #ff1744;
  --vp-c-brand-2: #f50057;
  --vp-c-brand-3: #c51162;

  /* Gradient - customize */
  --vp-home-hero-name-background: linear-gradient(
    135deg,
    #ff1744 0%,
    #f50057 50%,
    #c51162 100%
  );
}
```

### Change Logo

1. Add your logo to `docs/public/`
2. Update `.vitepress/config.mts`:

```ts
themeConfig: {
  logo: '/logo.svg',
  // ...
}
```

### Add Social Links

Edit `.vitepress/config.mts`:

```ts
socialLinks: [
  { icon: 'github', link: 'https://github.com/Matsuk1/JiETNG' },
  { icon: 'discord', link: 'https://discord.gg/your-server' },
  { icon: 'twitter', link: 'https://twitter.com/your-account' }
]
```

### Modify Navigation

Edit `.vitepress/config.mts`:

```ts
nav: [
  { text: 'Home', link: '/' },
  { text: 'Guide', link: '/guide/getting-started' },
  { text: 'New Section', link: '/new-section/' },
  // Add more...
]
```

### Update Footer

Edit `.vitepress/config.mts`:

```ts
footer: {
  message: 'Your custom message',
  copyright: 'Copyright © 2025 Your Name'
}
```

## Writing Documentation

### Markdown Basics

```md
# Heading 1
## Heading 2
### Heading 3

**Bold text**
*Italic text*
`Inline code`

[Link text](https://url.com)

![Image](./image.png)
```

### Custom Containers

```md
::: tip
This is a tip
:::

::: warning
This is a warning
:::

::: danger
Danger zone!
:::

::: details Click to expand
Hidden content here
:::
```

### Code Blocks

````md
```js
const hello = 'world'
console.log(hello)
```

```bash
npm install
npm run dev
```
````

### Tables

```md
| Feature | Status |
|---------|--------|
| Dark Mode | ✅ |
| Search | ✅ |
```

## File Organization

### Recommended Structure

```
docs/
├── guide/              # Getting started guides
│   ├── introduction.md
│   ├── getting-started.md
│   └── configuration.md
├── features/           # Feature documentation
│   ├── b50.md
│   ├── search.md
│   └── friends.md
├── commands/           # Command reference
│   ├── basic.md
│   ├── advanced.md
│   └── admin.md
├── more/               # Additional pages
│   ├── faq.md
│   ├── privacy.md
│   └── support.md
└── public/             # Static assets
    ├── images/
    └── favicon.ico
```

## Common Tasks

### Add a New Page

1. Create the file:

```bash
touch docs/features/new-feature.md
```

2. Add frontmatter:

```md
---
title: New Feature
description: Description of the feature
---

# New Feature

Content here...
```

3. Add to sidebar in `.vitepress/config.mts`:

```ts
sidebar: [
  {
    text: 'Features',
    items: [
      { text: 'New Feature', link: '/features/new-feature' }
    ]
  }
]
```

### Add Images

1. Put image in `docs/public/images/`
2. Reference in markdown:

```md
![Alt text](/images/screenshot.png)
```

### Add Custom Components

Create a Vue component:

```vue
<!-- docs/.vitepress/theme/components/CustomButton.vue -->
<template>
  <button class="custom-btn">
    <slot />
  </button>
</template>

<style scoped>
.custom-btn {
  /* styles */
}
</style>
```

Use in markdown:

```md
<script setup>
import CustomButton from './components/CustomButton.vue'
</script>

<CustomButton>Click me!</CustomButton>
```

## Troubleshooting

### Port Already in Use

```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9

# Or use different port
npm run docs:dev -- --port 3000
```

### Build Errors

```bash
# Clear cache
rm -rf docs/.vitepress/cache
rm -rf docs/node_modules

# Reinstall
npm install

# Rebuild
npm run docs:build
```

### Broken Links

Check build output for 404 warnings:

```bash
npm run docs:build
# Look for: "404 page not found" warnings
```

## Resources

### Official Documentation

- [VitePress Guide](https://vitepress.dev/guide/what-is-vitepress)
- [VitePress Config Reference](https://vitepress.dev/reference/site-config)
- [Markdown Extensions](https://vitepress.dev/guide/markdown)
- [Deployment Guide](https://vitepress.dev/guide/deploy)

### Examples

- [VitePress Examples](https://github.com/vuejs/vitepress/tree/main/docs)
- [Vue.js Docs](https://github.com/vuejs/docs) (built with VitePress)
- [Vite Docs](https://github.com/vitejs/vite/tree/main/docs)

## Support

Need help?

- 📖 Check VitePress [documentation](https://vitepress.dev/)
- 💬 Ask in [VitePress discussions](https://github.com/vuejs/vitepress/discussions)
- 🐛 Report issues: [GitHub Issues](https://github.com/Matsuk1/JiETNG/issues)

## What's Included

### Pages Created

- ✅ **Homepage** (`index.md`) - Hero section with 12 feature cards
- ✅ **Introduction** (`guide/introduction.md`) - Project overview
- ✅ **Getting Started** (`guide/getting-started.md`) - Setup guide
- ✅ **Best 50 Guide** (`features/b50.md`) - Comprehensive B50 docs
- ✅ **Basic Commands** (`commands/basic.md`) - Command reference
- ✅ **License** (`more/license.md`) - Legal information
- ✅ **Support** (`more/support.md`) - Help and contact

### Source Files Copied

- ✅ `README.md` → `README_SOURCE.md` (for reference)
- ✅ `README_EN.md` → `README_SOURCE_EN.md`
- ✅ `README_JP.md` → `README_SOURCE_JP.md`
- ✅ `LICENSE` → Converted to `more/license.md`

### Configuration

- ✅ Multi-language support (EN/JA/ZH)
- ✅ Search enabled
- ✅ Dark mode
- ✅ Custom gradients
- ✅ Animations
- ✅ Responsive design

## Next Actions Recommended

1. **Run the dev server** to see the site
2. **Review the content** and customize text
3. **Add missing pages** (FAQ, Privacy, etc.)
4. **Translate to Japanese/Chinese**
5. **Add your logo** to `public/`
6. **Update GitHub links** in config
7. **Deploy** to GitHub Pages or Vercel

---

**Ready to get started?**

```bash
cd /Users/matsuki/Desktop/JiETNG/docs
npm install
npm run docs:dev
```

Then visit: **http://localhost:5173**

Enjoy your new documentation website! 🎉

# JiETNG Documentation

This is the official documentation website for JiETNG, built with [VitePress](https://vitepress.dev/).

## Setup

1. Install dependencies:

```bash
cd docs
npm install
```

2. Run development server:

```bash
npm run docs:dev
```

The site will be available at `http://localhost:5173`

## Build

Build the static site for production:

```bash
npm run docs:build
```

Output will be in `docs/.vitepress/dist/`

## Preview

Preview the production build:

```bash
npm run docs:preview
```

## Deployment

### GitHub Pages

1. Build the site:
```bash
npm run docs:build
```

2. Deploy to GitHub Pages:
```bash
# Add to your repository
git add docs/.vitepress/dist -f
git commit -m "Deploy docs"
git subtree push --prefix docs/.vitepress/dist origin gh-pages
```

### Vercel/Netlify

Simply connect your GitHub repository. The build settings should be:

- **Build command**: `cd docs && npm install && npm run docs:build`
- **Output directory**: `docs/.vitepress/dist`
- **Node version**: 18+

## Project Structure

```
docs/
├── .vitepress/
│   ├── config.mts          # Site configuration
│   └── theme/
│       ├── index.ts        # Theme customization
│       └── style.css       # Custom styles
├── guide/                  # Getting started guides
│   ├── introduction.md
│   ├── getting-started.md
│   └── binding.md
├── features/               # Feature documentation
│   ├── b50.md
│   ├── search.md
│   └── ...
├── commands/               # Command reference
│   ├── basic.md
│   ├── advanced.md
│   └── admin.md
├── more/                   # Additional docs
│   ├── faq.md
│   ├── privacy.md
│   └── support.md
├── ja/                     # Japanese localization
├── zh/                     # Chinese localization
├── index.md                # Homepage
├── package.json
└── README.md               # This file
```

## Writing Documentation

### Creating a New Page

1. Create a Markdown file in the appropriate directory
2. Add frontmatter if needed:

```md
---
title: Page Title
description: Page description
---

# Page Title

Content here...
```

3. Add the page to the sidebar in `.vitepress/config.mts`

### Using Components

VitePress supports Vue components in Markdown:

```md
<script setup>
import CustomComponent from './CustomComponent.vue'
</script>

<CustomComponent />
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
This is a dangerous warning
:::

::: details Click to expand
Hidden content
:::
```

### Code Blocks

```md
```js
const msg = 'Hello'
console.log(msg)
` ` `
```

With line highlighting:

```md
```js{2}
const msg = 'Hello'
console.log(msg) // [!code highlight]
` ``
```

## Multi-Language Support

Add localized content in `ja/` and `zh/` directories with the same structure as root.

Example:
```
docs/
├── guide/
│   └── introduction.md       # English
├── ja/
│   └── guide/
│       └── introduction.md   # Japanese
└── zh/
    └── guide/
        └── introduction.md   # Chinese
```

## Maintenance

### Updating VitePress

```bash
npm update vitepress
```

### Adding Search

Search is enabled by default using VitePress's built-in local search.

## License

Copyright © 2025 Matsuki. All Rights Reserved.

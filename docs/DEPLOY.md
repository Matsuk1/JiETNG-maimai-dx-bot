# Deploying JiETNG Documentation

This guide explains how to deploy the JiETNG documentation website.

## Quick Start

1. **Install Dependencies**

```bash
cd /Users/matsuki/Desktop/JiETNG/docs
npm install
```

2. **Run Development Server**

```bash
npm run docs:dev
```


3. **Build for Production**

```bash
npm run docs:build
```

Output will be in `.vitepress/dist/`

## Deployment Options

### Option 1: GitHub Pages (Recommended)

#### Step 1: Build the site

```bash
npm run docs:build
```

#### Step 2: Create gh-pages branch

```bash
# From your project root
cd /Users/matsuki/Desktop/JiETNG/docs/.vitepress/dist

# Initialize git if not already
git init
git add -A
git commit -m 'Deploy documentation'

# Push to gh-pages branch
git push -f git@github.com:Matsuk1/JiETNG.git main:gh-pages
```

#### Step 3: Enable GitHub Pages

1. Go to your repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: `gh-pages` / `root`
4. Save

Your site will be at: `https://matsuk1.github.io/JiETNG/`

#### Automation with GitHub Actions

Create `.github/workflows/deploy-docs.yml`:

```yaml
name: Deploy Documentation

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: docs/package-lock.json

      - name: Install dependencies
        run: |
          cd docs
          npm ci

      - name: Build documentation
        run: |
          cd docs
          npm run docs:build

      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: docs/.vitepress/dist
```

Now documentation will auto-deploy on every push to `main` branch.

### Option 2: Vercel

1. **Sign up** at [vercel.com](https://vercel.com)

2. **Import** your GitHub repository

3. **Configure build settings**:
   - **Framework Preset**: VitePress
   - **Root Directory**: `docs`
   - **Build Command**: `npm run docs:build`
   - **Output Directory**: `.vitepress/dist`

4. **Deploy** - Vercel will auto-deploy on every push

Your site will be at: `https://jietng.vercel.app`

### Option 3: Netlify

1. **Sign up** at [netlify.com](https://netlify.com)

2. **New site from Git** → Connect to GitHub

3. **Build settings**:
   - **Base directory**: `docs`
   - **Build command**: `npm run docs:build`
   - **Publish directory**: `docs/.vitepress/dist`

4. **Deploy** - Auto-deploy on push

Your site will be at: `https://jietng.netlify.app`

### Option 4: Cloudflare Pages

1. **Sign up** at [pages.cloudflare.com](https://pages.cloudflare.com)

2. **Create a project** → Connect to GitHub

3. **Build configuration**:
   - **Framework preset**: None
   - **Build command**: `cd docs && npm install && npm run docs:build`
   - **Build output directory**: `docs/.vitepress/dist`

4. **Save and Deploy**

Your site will be at: `https://jietng.pages.dev`

### Option 5: Custom Server (Nginx)

1. **Build the site**:

```bash
npm run docs:build
```

2. **Copy files to server**:

```bash
scp -r .vitepress/dist/* user@your-server:/var/www/jietng-docs/
```

3. **Nginx configuration**:

```nginx
server {
    listen 80;
    server_name docs.jietng.com;

    root /var/www/jietng-docs;
    index index.html;

    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    # Enable gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

4. **Enable HTTPS** (recommended):

```bash
sudo certbot --nginx -d docs.jietng.com
```

## Custom Domain

### GitHub Pages

1. Add a `CNAME` file to `/docs/public/`:

```
docs.jietng.com
```

2. Configure DNS:
   - Type: `CNAME`
   - Name: `docs`
   - Value: `matsuk1.github.io`

3. In GitHub repo settings → Pages → Custom domain: `docs.jietng.com`

### Vercel/Netlify/Cloudflare

1. Go to project settings → Domains
2. Add custom domain: `docs.jietng.com`
3. Follow DNS instructions provided

## Environment Variables

If you need environment variables (API keys, etc.), create `.env`:

```bash
VITE_GITHUB_REPO=Matsuk1/JiETNG
VITE_LINE_BOT_URL=https://line.me/R/ti/p/@299bylay
```

Access in config:

```ts
export default defineConfig({
  // ...
  define: {
    __GITHUB_REPO__: JSON.stringify(process.env.VITE_GITHUB_REPO)
  }
})
```

## Updating Documentation

### Local Development

```bash
cd docs
npm run docs:dev
```

Edit files in `docs/` directory. Changes will hot-reload.

### Adding New Pages

1. Create a new `.md` file:

```bash
docs/features/new-feature.md
```

2. Add to sidebar in `.vitepress/config.mts`:

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

### Adding Multi-Language Pages

Create the same file in `ja/` and `zh/`:

```
docs/features/new-feature.md     (English)
docs/ja/features/new-feature.md  (Japanese)
docs/zh/features/new-feature.md  (Chinese)
```

## Maintenance

### Update VitePress

```bash
cd docs
npm update vitepress
```

### Check for Broken Links

```bash
npm run docs:build
# Look for 404 warnings in output
```

### Optimize Images

Use WebP format for better performance:

```bash
# Install converter
brew install webp

# Convert images
cwebp input.png -o output.webp
```

## Troubleshooting

### Build Fails

```bash
# Clear cache
rm -rf docs/.vitepress/cache
rm -rf docs/node_modules
npm install
npm run docs:build
```

### 404 on Deployment

Make sure your base URL is configured:

```ts
// .vitepress/config.mts
export default defineConfig({
  base: '/JiETNG/',  // For GitHub Pages at username.github.io/JiETNG/
  // OR
  base: '/',  // For custom domain
})
```

### Slow Build Times

1. Reduce number of pages
2. Optimize images
3. Disable sourcemaps in production:

```ts
export default defineConfig({
  vite: {
    build: {
      sourcemap: false
    }
  }
})
```

## Performance Tips

1. **Enable Caching**: Configure CDN caching for static assets
2. **Use WebP Images**: Smaller file sizes, faster loads
3. **Lazy Load Images**: Use `loading="lazy"` attribute
4. **Minimize Dependencies**: Only import what you need
5. **Enable Compression**: gzip or brotli compression

## Monitoring

### Add Analytics

Google Analytics example:

```ts
// .vitepress/config.mts
head: [
  ['script', {
    async: true,
    src: 'https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX'
  }],
  ['script', {}, `
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-XXXXXXXXXX');
  `]
]
```

### Monitor Uptime

Use services like:
- Uptime Robot (free)
- Pingdom
- StatusCake

---

## Quick Reference

```bash
# Development
npm run docs:dev           # Start dev server

# Production
npm run docs:build         # Build for production
npm run docs:preview       # Preview production build

# Deployment
git subtree push --prefix docs/.vitepress/dist origin gh-pages  # GitHub Pages
vercel --prod              # Vercel
netlify deploy --prod      # Netlify
```

---

For more information, see:
- [VitePress Documentation](https://vitepress.dev/)
- [Deployment Guide](https://vitepress.dev/guide/deploy)
- [Main README](./README.md)

# JiETNG 文档部署指南

本指南详细说明如何部署JiETNG文档网站的两种方式：GitHub Pages自动部署 和 本地构建手动部署。

## 前置准备

### 修复npm权限（如果需要）

如果遇到npm权限错误，在终端运行：

```bash
sudo chown -R 501:20 "/Users/matsuki/.npm"
```

或者删除并重建npm缓存：

```bash
rm -rf ~/.npm
mkdir ~/.npm
```

### 安装依赖

```bash
cd /Users/matsuki/Desktop/JiETNG/docs
npm install
```

---

## 选项 A: GitHub Pages 自动部署

### 步骤 1: 配置base路径

编辑 `docs/.vitepress/config.mts`：

**如果使用 username.github.io/JiETNG/ 格式：**
```typescript
base: '/JiETNG/',
```

**如果使用自定义域名（如 docs.jietng.com）：**
```typescript
base: '/',
```

当前配置已设置为 `/JiETNG/`。

### 步骤 2: 推送代码到GitHub

```bash
cd /Users/matsuki/Desktop/JiETNG

# 添加所有文件
git add .

# 提交
git commit -m "添加VitePress文档网站和GitHub Actions自动部署"

# 推送到main分支
git push origin main
```

### 步骤 3: GitHub Actions自动构建

推送后，GitHub Actions会自动：
1. 检测到 `docs/**` 目录的变化
2. 安装Node.js和依赖
3. 构建文档 (`npm run docs:build`)
4. 部署到 `gh-pages` 分支

查看构建状态：
- 访问 https://github.com/Matsuk1/JiETNG/actions
- 查看 "Deploy Documentation" 工作流

### 步骤 4: 启用GitHub Pages

1. 访问 https://github.com/Matsuk1/JiETNG/settings/pages
2. **Source**: 选择 "Deploy from a branch"
3. **Branch**: 选择 `gh-pages` 分支，目录选择 `/ (root)`
4. 点击 **Save**

### 步骤 5: 访问网站

等待1-2分钟后，访问：

**默认URL:**
```
https://matsuk1.github.io/JiETNG/
```

### 可选：自定义域名

如果你有自己的域名（如 docs.jietng.com）：

**A. 创建CNAME文件**

创建 `docs/public/CNAME`：
```
docs.jietng.com
```

**B. 配置DNS**

在你的域名提供商添加DNS记录：
```
类型: CNAME
名称: docs
值: matsuk1.github.io
```

**C. 更新base路径**

编辑 `docs/.vitepress/config.mts`：
```typescript
base: '/',  // 自定义域名使用根路径
```

**D. 在GitHub Pages设置自定义域名**

1. 访问 https://github.com/Matsuk1/JiETNG/settings/pages
2. **Custom domain**: 输入 `docs.jietng.com`
3. 勾选 **Enforce HTTPS**
4. 保存

### 自动更新

以后每次你修改 `docs/` 目录下的文件并推送到GitHub：
```bash
git add docs/
git commit -m "更新文档"
git push origin main
```

GitHub Actions会自动重新构建和部署！

---

## 选项 D: 本地构建

### 方式 1: 本地预览（开发模式）

**启动开发服务器：**

```bash
cd /Users/matsuki/Desktop/JiETNG/docs
npm run docs:dev
```

**访问：** http://localhost:5173

**特点：**
- ✅ 热重载（修改文件自动刷新）
- ✅ 快速启动
- ✅ 适合开发和预览
- ❌ 不适合生产环境

**停止服务器：** 按 `Ctrl + C`

### 方式 2: 本地构建（生产模式）

**构建静态文件：**

```bash
cd /Users/matsuki/Desktop/JiETNG/docs
npm run docs:build
```

**输出目录：** `docs/.vitepress/dist/`

**预览构建结果：**

```bash
npm run docs:preview
```

**访问：** http://localhost:4173

### 方式 3: 部署到自己的服务器

**1. 构建文件**

```bash
cd /Users/matsuki/Desktop/JiETNG/docs
npm run docs:build
```

**2. 复制文件到服务器**

使用scp：
```bash
scp -r docs/.vitepress/dist/* user@your-server:/var/www/jietng-docs/
```

或使用rsync：
```bash
rsync -avz docs/.vitepress/dist/ user@your-server:/var/www/jietng-docs/
```

**3. 配置Nginx**

创建 `/etc/nginx/sites-available/jietng-docs`：

```nginx
server {
    listen 80;
    server_name docs.jietng.com;

    root /var/www/jietng-docs;
    index index.html;

    location / {
        try_files $uri $uri/ $uri.html =404;
    }

    # 启用gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 缓存静态资源
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**启用站点：**
```bash
sudo ln -s /etc/nginx/sites-available/jietng-docs /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**4. 配置HTTPS（推荐）**

```bash
sudo certbot --nginx -d docs.jietng.com
```

### 方式 4: 部署到其他静态托管服务

**构建文件：**
```bash
npm run docs:build
```

**上传 `docs/.vitepress/dist/` 目录到：**

- **Netlify**: 拖拽上传或连接Git
- **Vercel**: 导入GitHub仓库
- **Cloudflare Pages**: 连接GitHub
- **Firebase Hosting**: `firebase deploy`
- **AWS S3**: `aws s3 sync`

---

## 常见问题

### 1. npm权限错误

**错误信息：**
```
npm error code EACCES
npm error syscall mkdir
npm error path /Users/matsuki/.npm/_cacache/...
```

**解决方案：**
```bash
sudo chown -R 501:20 "/Users/matsuki/.npm"
```

或：
```bash
rm -rf ~/.npm
mkdir ~/.npm
npm cache clean --force
```

### 2. GitHub Actions构建失败

**检查步骤：**
1. 访问 https://github.com/Matsuk1/JiETNG/actions
2. 点击失败的工作流
3. 查看错误日志

**常见原因：**
- Node.js版本不兼容
- 依赖安装失败
- 构建命令错误

**解决方案：**
- 检查 `package.json` 中的依赖版本
- 本地测试构建：`npm run docs:build`
- 更新 `.github/workflows/deploy-docs.yml`

### 3. GitHub Pages 404错误

**可能原因：**
1. base路径配置错误
2. gh-pages分支未正确生成
3. GitHub Pages未启用

**解决方案：**

**检查base路径：**
```typescript
// docs/.vitepress/config.mts
// 对于 username.github.io/JiETNG/
base: '/JiETNG/',

// 对于自定义域名
base: '/',
```

**检查gh-pages分支：**
```bash
git fetch origin
git branch -a | grep gh-pages
```

**重新部署：**
```bash
git add .
git commit -m "修复base路径"
git push origin main
```

### 4. 样式/资源加载失败

**原因：** base路径配置错误

**检查方法：**
- 打开浏览器开发者工具
- 查看Network标签
- 检查失败的请求路径

**解决方案：**
确保 `base` 配置与实际部署路径匹配。

### 5. 本地构建慢

**优化方案：**
```bash
# 清除缓存
rm -rf docs/.vitepress/cache
rm -rf docs/.vitepress/dist

# 重新构建
npm run docs:build
```

---

## 更新文档

### 本地更新流程

1. **修改文档文件**
   ```bash
   cd /Users/matsuki/Desktop/JiETNG/docs
   # 编辑 .md 文件
   ```

2. **本地预览**
   ```bash
   npm run docs:dev
   # 访问 http://localhost:5173 查看效果
   ```

3. **提交到Git**
   ```bash
   git add docs/
   git commit -m "更新文档内容"
   git push origin main
   ```

4. **自动部署**
   - GitHub Actions自动构建
   - 1-2分钟后网站更新

### 添加新页面

1. **创建Markdown文件**
   ```bash
   touch docs/features/new-feature.md
   ```

2. **添加到侧边栏**
   编辑 `docs/.vitepress/config.mts`：
   ```typescript
   sidebar: [
     {
       text: 'Features',
       items: [
         { text: 'New Feature', link: '/features/new-feature' }
       ]
     }
   ]
   ```

3. **提交并推送**
   ```bash
   git add docs/
   git commit -m "添加新功能文档"
   git push origin main
   ```

---

## 快速命令参考

```bash
# 安装依赖
cd /Users/matsuki/Desktop/JiETNG/docs
npm install

# 开发模式（热重载）
npm run docs:dev
# 访问 http://localhost:5173

# 生产构建
npm run docs:build

# 预览构建结果
npm run docs:preview
# 访问 http://localhost:4173

# 提交到GitHub（自动部署）
git add .
git commit -m "更新文档"
git push origin main

# 清除缓存
rm -rf docs/.vitepress/cache
rm -rf docs/.vitepress/dist
rm -rf docs/node_modules
npm install
```

---

## 技术支持

遇到问题？

1. **查看日志**
   - GitHub Actions: https://github.com/Matsuk1/JiETNG/actions
   - 本地构建: 查看终端输出

2. **检查文档**
   - VitePress官方文档: https://vitepress.dev/
   - GitHub Pages文档: https://docs.github.com/pages

3. **寻求帮助**
   - 提交Issue: https://github.com/Matsuk1/JiETNG/issues
   - 查看已有的部署文档: `DEPLOY.md`, `SETUP_GUIDE.md`

---

## 下一步

✅ 文档网站已配置完成
✅ GitHub Actions自动部署已设置
✅ 本地构建方式已准备就绪

**现在你可以：**

1. 推送代码到GitHub，启用自动部署
2. 本地运行 `npm run docs:dev` 预览效果
3. 添加更多文档内容
4. 配置自定义域名（可选）

祝部署顺利！🚀

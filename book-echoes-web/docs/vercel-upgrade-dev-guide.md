# Vercel 云化升级开发文档（方案一）

## 1. 项目目标与范围
- 将所有图片（原图、缩略图）及字体资源迁移至 Cloudflare R2，避免 Git 仓库存储膨胀。
- 兼容 1 万日访问、1 万数据量，保证图文内容可持续扩展。
- 完成字体 Web 化，保持视觉一致性。
- 调整 Next.js/Vercel 构建、运行、缓存策略，确保部署稳定。

## 2. 当前状态简述
- 技术栈：Next.js 16 + React 19，前端以静态数据渲染为主。
- 构建脚本：`scripts/build-content.mjs` 在数据初始化时生成 `public/content`、`metadata.json` 等资源。
- 静态资源：`public/content/<month>/<barcode>/` 下堆积原图与缩略图。
- 字体：本地安装字体（上图东观体、又又意宋等）在 `globals.css` 里直接引用，部署后不可用。

## 3. 目标架构设计
```
数据源（sources_data）
    └─ build-content.mjs （生成元数据 + 触发 R2 上传）
Cloudflare R2
    ├─ /content/**        # 原图、缩略图
    └─ /fonts/**          # 转换后的 woff2 字体
Next.js（Vercel）
    ├─ 直接消费 metadata.json 中的 R2 URL
    ├─ next/image 远程加载 + 缓存
    └─ 全站静态化/ISR，revalidate 控制
```

## 4. 实施阶段与任务列表
| 阶段 | 任务 | 产出 |
| --- | --- | --- |
| 准备 | Cloudflare 账号、R2 Bucket、公共域名、API Tokens | R2 Endpoint、AccessKey、Secret、Public Domain |
| 字体 Web 化 | `.ttf/.otf -> .woff2`，上传 `/fonts`，`globals.css` 引入 | 字体 URL、CSS 定义 |
| 图片迁移 | 安装 `@aws-sdk/client-s3`，在构建脚本中加入上传逻辑，更新 metadata | R2 URL 写入 metadata，`public/content` 可精简 |
| 前端适配 | 抽象图片 URL 生成、替换 `<img>` 为 `next/image`、配置 remotePatterns | 前端读取 R2 资源稳定 |
| 部署配置 | Vercel 环境变量、Build 命令、缓存策略（`revalidate`/`dynamic`） | 可重复部署流水线 |
| 验证与优化 | 图片/字体加载验证、Vercel 预览链路、性能 & 容量测试 | 验证报告 |

## 5. 详细步骤
### 5.1 Cloudflare R2 准备
1. 创建 R2 Bucket（建议 `book-echoes`），开启公共域名（R2 自带或自定义 Workers/域名）。
2. 生成 API Token，授权 `Edit` bucket。
3. 记录以下变量供 `.env` 与 Vercel 使用：
   - `R2_ENDPOINT=https://<accountid>.r2.cloudflarestorage.com`
   - `R2_BUCKET_NAME=book-echoes`
   - `R2_PUBLIC_URL=https://<cdn-domain>`
   - `R2_ACCESS_KEY_ID=...`
   - `R2_SECRET_ACCESS_KEY=...`

### 5.2 字体流程
1. 当前 `.woff` 字体文件统一存放在 `public/fonts`（本地源目录），可直接在该目录中执行批量处理；若仍保留 `.ttf/.otf` 原文件，可同步放置在相同层级以便版本管理。
   ```bash
   npx ttf2woff2 ShangTu.ttf > shangtu-dongguan.woff2
   ```
2. 使用 `fonttools` 或 `ttf2woff2` 将原始字体压缩为 `.woff2`（必要时保留 `.woff` 作为 fallback），并上传至 `book-echoes/fonts/`，保持与 `public/fonts` 一致的命名结构以方便引用。
3. `app/globals.css` 中通过 R2 URL 引入，并指定 `font-display: swap`：
   ```css
   @font-face {
     font-family: 'ShangTuDongGuan';
     src: url('https://cdn.example.com/fonts/shangtu-dongguan.woff2') format('woff2');
     font-weight: 400;
     font-style: normal;
     font-display: swap;
   }
   ```
4. 在组件或 CSS 变量中复用新字体名，必要时提供 `Noto Serif SC` 等 fallback。

### 5.3 图片上传与 metadata 改造
1. 安装依赖：`npm install @aws-sdk/client-s3`.
2. 在 `scripts/build-content.mjs` 中：
   - 初始化 `S3Client` 指向 R2。
   - 在生成缩略图后，调用 `uploadToR2(localPath, key, contentType)`，同步上传原图与缩略图。
   - `metadata.json` 中记录完整 URL，例如 `https://cdn.example.com/content/2025-09/xxxx/thumb.jpg`.
   - 保留可配置开关（如 `UPLOAD_TO_R2=false`）方便本地调试。
3. 迁移历史数据：编写一次性脚本遍历 `public/content` 并上传，生成 R2 路径与校验日志。
4. 清理策略：迁移完成后可将 `public/content` 目录保留少量示例或忽略提交，依赖 `.gitignore`.

### 5.4 前端适配
1. 在统一工具函数中解析图片/字体 URL，例如 `lib/assets.ts`：
   ```ts
   export function resolveImageUrl(path: string) {
     if (path.startsWith('http')) return path;
     return `${process.env.NEXT_PUBLIC_R2_PUBLIC_URL}/${path}`;
   }
   ```
2. 全量替换成 `next/image`，利用 `placeholder="blur"`、`sizes`、`loading="lazy"`。
3. `next.config.ts` 中新增：
   ```ts
   images: {
     remotePatterns: [{
       protocol: 'https',
       hostname: 'cdn.example.com',
       pathname: '/content/**',
     }],
     formats: ['image/avif', 'image/webp'],
   }
   ```
4. 若采用渐进迁移，`resolveImageUrl` 里对时间或标志位分支处理（R2 vs 本地）。

### 5.5 构建与部署
1. `.env.local` 配置 R2 与公共 URL，同步到 Vercel 环境变量（Production/Preview/Development）。
2. 构建命令仍为 `npm run build`；若上传耗时，改为本地/CI 预处理后提交 metadata。
3. 根据内容更新频率设置：
   - `export const revalidate = 3600;`（每小时刷新）
   - 或 `export const dynamic = 'force-static';` 配合手动触发再生成。
4. 可选：若完全静态，设置 `output: 'export'` 并通过 `vercel-static-build` 发布。

### 5.6 验证
- 本地运行 `npm run dev`，确认图片与字体 URL 均从 CDN 加载且无 404。
- Vercel Preview：检查 `Image Optimization` 是否命中、首屏是否加载 R2 字体。
- Lighthouse 指标需维持 LCP < 2.5s，CLS ≈ 0。
- 容量预估：按每日 10k PV、平均 5 张 100KB 图片，月度带宽约 50GB，R2 出站免费，Vercel Hobby 足够。

## 6. 运维与自动化
- 建议新增 GitHub Actions（可选）：
  - 当 `sources_data/**` 变动时触发构建脚本并上传 R2。
  - 构建完成后将 metadata 推回仓库，确保可追溯。
- R2 提供对象生命周期，可针对旧图片设置低频访问存储或备份到别的 Bucket。
- 监控：
  - Vercel Analytics 观测流量峰值。
  - Cloudflare Dashboard 查看 Bucket 访问量与错误率。

## 7. 风险与应对
| 风险 | 描述 | 缓解措施 |
| --- | --- | --- |
| 字体版权 | 商用版权不明 | 逐一核实授权，必要时更换开源字体 |
| 上传失败 / 超时 | 构建脚本在 CI 执行时可能因网络波动失败 | 加入重试、断点续传、失败后保留本地回退 |
| 存量数据缺失 | 迁移过程遗漏文件，导致页面 404 | 迁移脚本对比本地/远程文件数与 hash，生成校验报告 |
| CDN 缓存失效 | 字体、图片更新后旧缓存未刷新 | R2 URL 中加入版本号或 Query；必要时执行 CDN Purge |

## 8. 交付清单
- `scripts/build-content.mjs`：R2 上传逻辑、配置开关。
- `lib/assets.ts`（或等价模块）：统一资源 URL 解析。
- `app/globals.css`：全部字体改为 R2 URL，提供 fallback。
- `next.config.ts`：remotePatterns、图片格式优化、可选 `output`/`revalidate`。
- `docs/vercel-upgrade-dev-guide.md`（本文档）：沉淀所有步骤。

## 9. 下一步建议
1. 先完成字体 Web 化与 Vercel 环境变量配置，验证最小可行链路。
2. 编写图片迁移脚本并在小批次数据上演练，生成迁移日志模板。
3. 将构建脚本与迁移脚本纳入 CI/CD，确保后续数据更新无需人工干预。

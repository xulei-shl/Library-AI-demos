# 前端开发总结 (Frontend Development Summary)

**日期**: 2025-11-20
**版本**: 0.1.0

## 1. 概述
本文档总结了“书海回响” (Book Echoes) 项目的前端开发工作。项目基于 Next.js 框架，实现了 PRD 中描述的“数字目录柜”核心隐喻，包括首页网格视图、沉浸式画布视图以及复杂的交互动画。

## 2. 技术栈与依赖
*   **核心框架**: Next.js 16 (App Router)
*   **语言**: TypeScript
*   **样式**: Tailwind CSS v4
*   **动画**: Framer Motion (用于复杂的布局流转和手势交互)
*   **状态管理**: Zustand (管理全局视图状态和选中书籍)
*   **工具库**: `clsx`, `tailwind-merge`

## 3. 核心架构实现

### 3.1 全局样式与主题 (`app/globals.css`)
*   配置了 PRD 指定的色卡：
    *   背景色: `#F2F0E9` (米白)
    *   文字色: `#2C2C2C` (炭黑)
    *   强调色: `#8B3A3A` (铁锈红)
*   定义了中西合璧的字体系统变量 (`--font-display`, `--font-body`, `--font-accent`)。
*   实现了全局噪点纹理 (`.noise-overlay`) 以模拟纸张质感。

### 3.2 状态管理 (`store/useStore.ts`)
使用 Zustand 创建了轻量级全局 Store，管理以下状态：
*   `viewMode`: 当前视图模式 ('archive' | 'canvas')
*   `selectedMonth`: 当前选中的月份
*   `focusedBookId`: 当前聚焦的书籍 ID
*   `scatterPositions`: 记录书籍在散落状态下的随机位置和角度

### 3.3 组件体系 (`components/`)

#### A. 首页归档 (`ArchiveGrid.tsx`)
*   实现了全屏网格布局。
*   添加了鼠标悬停时的“卡片探出”微交互动画。
*   点击月份卡片导航至详情页。

#### B. 沉浸画布 (`Canvas.tsx`)
*   核心容器组件，负责编排书籍的展示。
*   根据 `focusedBookId` 切换“散落”与“聚焦”两种状态。
*   集成 `Dock` 和 `InfoPanel` 组件。

#### C. 书籍卡片 (`BookCard.tsx`)
*   实现了三种状态的视觉呈现：
    *   **Scatter (散落)**: 随机位置分布，支持拖拽交互 (Framer Motion drag)。
    *   **Focused (聚焦)**: 选中卡片使用 `layoutId` 平滑过渡到左侧固定位置；背景卡片淡化处理。
    *   **Dock (底栏)**: 缩略图展示，支持悬停放大。

#### D. 信息面板 (`InfoPanel.tsx`)
*   右侧滑出的详情面板。
*   展示书籍元数据、评分、推荐语及深度阅读内容。
*   实现了目录的折叠/展开交互。

#### E. 底部导航 (`Dock.tsx`)
*   仿 macOS Dock 的底部导航栏。
*   包含鱼眼放大效果，支持快速切换聚焦书籍。

### 3.4 页面与路由 (`app/`)

#### A. 首页 (`page.tsx`)
*   渲染 `ArchiveGrid` 组件。
*   加载全局噪点背景。

#### B. 月份详情页 (`[month]/page.tsx`)
*   动态路由页面，根据 URL 参数读取对应月份数据。
*   读取 `content/[month]/metadata.json` 文件。
*   使用 `lib/utils.ts` 中的 `transformMetadataToBook` 函数将中文元数据映射为前端 TypeScript 接口。

### 3.5 API 路由 (`app/api/`)
*   **图片服务**: `api/images/[month]/[id]/[type]/route.ts`
    *   动态服务本地 `content` 目录下的图片资源。
    *   支持 `cover` (封面原图) 和 `thumbnail` (缩略图) 两种类型。

## 4. 数据流转
1.  构建脚本生成 `content/[month]/metadata.json` 和图片资源。
2.  `[month]/page.tsx` 在服务端读取 JSON 数据。
3.  数据经过转换后传递给 `Canvas` 组件。
4.  `Canvas` 组件初始化 Zustand Store，并渲染 `BookCard` 列表。
5.  用户交互触发 Zustand 状态更新，Framer Motion 响应状态变化执行动画。

## 5. 后续优化建议
*   **字体加载**: 目前仅定义了字体名称，需引入实际字体文件或配置 Web Font。
*   **图片优化**: 当前 API 路由直接读取文件，建议添加缓存策略或使用 Next.js Image 优化。
*   **移动端适配**: 当前主要针对桌面端优化，需进一步完善移动端触摸交互体验。

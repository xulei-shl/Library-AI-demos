# UI 设计系统规范文档
- **Status**: Proposal
- **Date**: 2025-12-22

## 1. 目标与背景
定义《墨迹与边界》的视觉语言系统，确保所有组件遵循统一的颜色、间距、字体、动画曲线与响应式规则。本文档是 `@.rules/05_UIUX_DESIGNER.md` 在项目中的具体落地，为 `NarrativeMap`、`InkLine`、`RippleNode`、`PlaybackControl` 等模块提供设计令牌（Design Tokens）。

## 2. 详细设计
### 2.1 颜色系统 (Color Palette)
基于需求文档 `@docs/墨迹与边界-0.3.md` 第 2.1 节。

#### 主题色
```typescript
// src/core/theme/colors.ts
export const THEME_COLORS = {
  // 底图纸张纹理
  paper: {
    light: '#F5F5F0',
    dark: '#1a1a1a',
  },
  // 墨迹主色（作者默认）
  ink: {
    primary: '#2C3E50',   // 深蓝灰
    secondary: '#8B4513', // 棕褐
    accent: '#D4AF37',    // 金色（用户标记）
  },
  // 交互状态
  interactive: {
    hover: 'rgba(0, 0, 0, 0.1)',
    focus: '#4A90E2',
    disabled: '#CCCCCC',
  },
  // 语义色
  semantic: {
    error: '#E74C3C',
    warning: '#F39C12',
    success: '#27AE60',
  },
} as const;
```

#### 作者主题色分配
- 村上春树: `#2C3E50`
- 马尔克斯: `#F4D03F`
- 卡夫卡: `#8B4513`
- 用户自定义: 支持 HSL 色轮选择，自动校验对比度 ≥ 4.5:1

### 2.2 间距与尺寸 (Spacing & Sizing)
遵循 8px 基准网格。

```typescript
// src/core/theme/spacing.ts
export const SPACING = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
} as const;

export const NODE_SIZES = {
  default: 8,      // 默认节点半径
  hover: 12,       // Hover 放大
  breathing: 16,   // 呼吸光晕外径
} as const;
```

### 2.3 字体系统 (Typography)
```typescript
// src/core/theme/typography.ts
export const TYPOGRAPHY = {
  fontFamily: {
    sans: '"Inter", "Noto Sans SC", sans-serif',
    mono: '"Fira Code", monospace',
  },
  fontSize: {
    xs: '12px',
    sm: '14px',
    base: '16px',
    lg: '20px',
    xl: '24px',
    '2xl': '32px',  // 年份指示器
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
} as const;
```

### 2.4 动画曲线 (Animation Easing)
基于需求文档的"墨迹生长"与"涟漪"动画。

```typescript
// src/core/theme/animations.ts
export const EASING = {
  // 墨迹线条生长（缓入缓出）
  inkGrowth: 'cubic-bezier(0.4, 0.0, 0.2, 1)',
  // 涟漪扩散（快速启动，慢速结束）
  ripple: 'cubic-bezier(0.0, 0.0, 0.2, 1)',
  // Smart FlyTo 相机运动（物理感）
  camera: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
  // UI 元素进出（标准）
  ui: 'cubic-bezier(0.4, 0.0, 0.6, 1)',
} as const;

export const DURATIONS = {
  fast: 150,       // Tooltip 显示
  normal: 300,     // 按钮交互
  slow: 600,       // 涟漪动画
  narrative: 1000, // 墨迹生长基准（会根据年份跨度调整）
} as const;
```

### 2.5 阴影与层级 (Shadows & Z-Index)
```typescript
// src/core/theme/shadows.ts
export const SHADOWS = {
  // 线条悬浮阴影（需求 2.1 节）
  inkLine: '0 2px 4px rgba(0, 0, 0, 0.1)',
  // 节点阴影
  node: '0 1px 3px rgba(0, 0, 0, 0.12)',
  // Tooltip 阴影
  tooltip: '0 4px 12px rgba(0, 0, 0, 0.15)',
  // 控制栏阴影
  control: '0 -2px 8px rgba(0, 0, 0, 0.1)',
} as const;

export const Z_INDEX = {
  base: 0,          // 底图
  inkLines: 10,     // 线条层
  nodes: 20,        // 节点层
  constellation: 25,// 用户标记层
  tooltip: 100,     // Tooltip
  controls: 200,    // 播放控制栏
  modal: 1000,      // 模态框
} as const;
```

### 2.6 响应式断点 (Breakpoints)
```typescript
// src/core/theme/breakpoints.ts
export const BREAKPOINTS = {
  mobile: 640,   // 手机
  tablet: 768,   // 平板
  desktop: 1024, // 桌面
  wide: 1440,    // 宽屏
} as const;

// Tailwind 配置同步
export const TAILWIND_SCREENS = {
  sm: `${BREAKPOINTS.mobile}px`,
  md: `${BREAKPOINTS.tablet}px`,
  lg: `${BREAKPOINTS.desktop}px`,
  xl: `${BREAKPOINTS.wide}px`,
};
```

### 2.7 可访问性规范 (Accessibility)
- **对比度**: 所有文本与背景对比度 ≥ 4.5:1（WCAG AA）。
- **焦点指示**: 键盘焦点使用 `focus` 颜色 + 2px 实线外框。
- **动画降级**: 检测 `prefers-reduced-motion`，禁用非关键动画。
- **触控目标**: 所有可交互元素最小尺寸 44x44px（移动端）。

## 3. 实现策略
### 3.1 技术选型
- **CSS-in-JS**: 使用 `vanilla-extract` 或 `Tailwind CSS` + CSS Variables。
- **主题切换**: 通过 `data-theme="light|dark"` 属性切换颜色变量。
- **类型安全**: 所有 Design Tokens 导出为 TypeScript 常量。

### 3.2 文件结构
```
src/core/theme/
├── colors.ts
├── spacing.ts
├── typography.ts
├── animations.ts
├── shadows.ts
├── breakpoints.ts
└── index.ts  // 统一导出
```

### 3.3 使用示例
```typescript
import { THEME_COLORS, SPACING, EASING } from '@/core/theme';

const inkLineStyle = {
  stroke: THEME_COLORS.ink.primary,
  strokeWidth: 2,
  filter: `drop-shadow(${SHADOWS.inkLine})`,
  transition: `stroke-dashoffset ${DURATIONS.narrative}ms ${EASING.inkGrowth}`,
};
```

## 4. 测试策略
1. **对比度校验**: 使用 `polished` 库的 `readableColor` 函数自动测试所有颜色组合。
2. **响应式测试**: Storybook 集成 `@storybook/addon-viewport`，覆盖所有断点。
3. **可访问性扫描**: 使用 `jest-axe` 与 `Lighthouse` 自动化检测。
4. **视觉回归**: 使用 `Chromatic` 或 `Percy` 捕获组件快照。

## 5. 依赖声明
- 本文档为所有 UI 组件的设计基础。
- 与 `@.rules/05_UIUX_DESIGNER.md` 保持一致。
- 需在 Sprint 0 完成后立即实施，作为后续开发的前置依赖。

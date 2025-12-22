/**
 * 字体系统
 * 参考：@docs/design/ui_design_system_20251222.md
 */

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
    '2xl': '32px', // 年份指示器
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const;

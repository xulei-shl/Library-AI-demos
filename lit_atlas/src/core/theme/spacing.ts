/**
 * 间距与尺寸系统 - 基于 8px 网格
 * 参考：@docs/design/ui_design_system_20251222.md
 */

export const SPACING = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
} as const;

export const NODE_SIZES = {
  default: 8, // 默认节点半径
  hover: 12, // Hover 放大
  breathing: 16, // 呼吸光晕外径
} as const;

/**
 * 触控目标最小尺寸（移动端可访问性）
 */
export const TOUCH_TARGET = {
  minWidth: 44,
  minHeight: 44,
} as const;

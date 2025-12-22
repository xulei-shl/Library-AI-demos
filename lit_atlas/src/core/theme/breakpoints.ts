/**
 * 响应式断点
 * 参考：@docs/design/ui_design_system_20251222.md
 */

export const BREAKPOINTS = {
  mobile: 640, // 手机
  tablet: 768, // 平板
  desktop: 1024, // 桌面
  wide: 1440, // 宽屏
} as const;

/**
 * Tailwind 配置同步
 */
export const TAILWIND_SCREENS = {
  sm: `${BREAKPOINTS.mobile}px`,
  md: `${BREAKPOINTS.tablet}px`,
  lg: `${BREAKPOINTS.desktop}px`,
  xl: `${BREAKPOINTS.wide}px`,
};

/**
 * 媒体查询工具函数
 */
export const mediaQuery = {
  mobile: `@media (max-width: ${BREAKPOINTS.mobile - 1}px)`,
  tablet: `@media (min-width: ${BREAKPOINTS.mobile}px) and (max-width: ${BREAKPOINTS.tablet - 1}px)`,
  desktop: `@media (min-width: ${BREAKPOINTS.tablet}px)`,
  wide: `@media (min-width: ${BREAKPOINTS.wide}px)`,
};

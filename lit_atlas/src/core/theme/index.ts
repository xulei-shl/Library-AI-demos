/**
 * 设计系统统一导出
 * 参考：@docs/design/ui_design_system_20251222.md
 */

export * from './colors';
export * from './spacing';
export * from './typography';
export * from './animations';
export * from './shadows';
export * from './breakpoints';
export * from './paperTexture';

// Re-export commonly used items
export { NODE_SIZES, TOUCH_TARGET } from './spacing';

/**
 * 主题配置类型
 */
export type Theme = {
  mode: 'light' | 'dark';
};

/**
 * 默认主题
 */
export const DEFAULT_THEME: Theme = {
  mode: 'light',
};

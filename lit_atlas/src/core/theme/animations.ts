/**
 * 动画曲线与时长
 * 参考：@docs/design/ui_design_system_20251222.md
 */

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
  fast: 150, // Tooltip 显示
  normal: 300, // 按钮交互
  slow: 600, // 涟漪动画
  narrative: 1000, // 墨迹生长基准（会根据年份跨度调整）
} as const;

/**
 * 检测用户是否偏好减少动画
 */
export const prefersReducedMotion = (): boolean => {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

/**
 * 根据用户偏好调整动画时长
 */
export const getAdjustedDuration = (duration: number): number => {
  return prefersReducedMotion() ? Math.min(duration * 0.3, 300) : duration;
};

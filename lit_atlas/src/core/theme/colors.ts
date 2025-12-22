/**
 * 颜色系统 - 墨迹与边界
 * 参考：@docs/design/ui_design_system_20251222.md
 */

export const THEME_COLORS = {
  // 底图纸张纹理
  paper: {
    light: '#F5F5F0',
    dark: '#1a1a1a',
  },
  // 墨迹主色（作者默认）
  ink: {
    primary: '#2C3E50', // 深蓝灰
    secondary: '#8B4513', // 棕褐
    accent: '#D4AF37', // 金色（用户标记）
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
  // 作者主题色
  authors: {
    murakami: '#2C3E50', // 村上春树 - 深蓝灰
    marquez: '#F4D03F', // 马尔克斯 - 金黄
    kafka: '#8B4513', // 卡夫卡 - 棕褐
    woolf: '#9B59B6', // 伍尔夫 - 紫色
    borges: '#E67E22', // 博尔赫斯 - 橙色
  },
} as const;

/**
 * 颜色工具函数
 */
export const colorUtils = {
  /**
   * 将十六进制颜色转换为 RGBA
   */
  hexToRgba: (hex: string, alpha: number): string => {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  },

  /**
   * 混合两个颜色（用于 Overlay 模式）
   */
  blendColors: (color1: string, color2: string, _ratio = 0.5): string => {
    // 简化实现，实际应使用更复杂的混色算法
    return color1; // TODO: 实现真正的颜色混合
  },
};

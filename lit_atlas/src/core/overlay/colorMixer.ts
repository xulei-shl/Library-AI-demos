/**
 * 颜色混合工具
 * 参考：@docs/design/overlay_mode_module_20251215.md
 */

/**
 * RGB 颜色
 */
interface RGB {
  r: number;
  g: number;
  b: number;
}

/**
 * HSL 颜色
 */
interface HSL {
  h: number;
  s: number;
  l: number;
}

/**
 * 将 Hex 颜色转换为 RGB
 */
function hexToRgb(hex: string): RGB {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result) {
    throw new Error(`Invalid hex color: ${hex}`);
  }
  return {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16),
  };
}

/**
 * 将 RGB 转换为 Hex
 */
function rgbToHex(rgb: RGB): string {
  const toHex = (n: number) => {
    const hex = Math.round(n).toString(16);
    return hex.length === 1 ? '0' + hex : hex;
  };
  return `#${toHex(rgb.r)}${toHex(rgb.g)}${toHex(rgb.b)}`;
}

/**
 * 将 RGB 转换为 HSL
 */
function rgbToHsl(rgb: RGB): HSL {
  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;

  if (max === min) {
    return { h: 0, s: 0, l };
  }

  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

  let h = 0;
  switch (max) {
    case r:
      h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      break;
    case g:
      h = ((b - r) / d + 2) / 6;
      break;
    case b:
      h = ((r - g) / d + 4) / 6;
      break;
  }

  return { h: h * 360, s, l };
}

/**
 * 将 HSL 转换为 RGB
 */
function hslToRgb(hsl: HSL): RGB {
  const h = hsl.h / 360;
  const s = hsl.s;
  const l = hsl.l;

  if (s === 0) {
    const gray = Math.round(l * 255);
    return { r: gray, g: gray, b: gray };
  }

  const hue2rgb = (p: number, q: number, t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };

  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;

  return {
    r: Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
    g: Math.round(hue2rgb(p, q, h) * 255),
    b: Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
  };
}

/**
 * 计算相对亮度（用于对比度计算）
 */
function getRelativeLuminance(rgb: RGB): number {
  const rsRGB = rgb.r / 255;
  const gsRGB = rgb.g / 255;
  const bsRGB = rgb.b / 255;

  const r = rsRGB <= 0.03928 ? rsRGB / 12.92 : Math.pow((rsRGB + 0.055) / 1.055, 2.4);
  const g = gsRGB <= 0.03928 ? gsRGB / 12.92 : Math.pow((gsRGB + 0.055) / 1.055, 2.4);
  const b = bsRGB <= 0.03928 ? bsRGB / 12.92 : Math.pow((bsRGB + 0.055) / 1.055, 2.4);

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * 计算对比度
 */
function getContrastRatio(color1: RGB, color2: RGB): number {
  const l1 = getRelativeLuminance(color1);
  const l2 = getRelativeLuminance(color2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * 在 HSL 空间混合两个颜色
 * 避免产生灰色，保持饱和度
 */
export function mixColors(color1: string, color2: string, ratio: number = 0.5): string {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);

  const hsl1 = rgbToHsl(rgb1);
  const hsl2 = rgbToHsl(rgb2);

  // 混合色相（处理环形空间）
  let h1 = hsl1.h;
  let h2 = hsl2.h;
  const diff = Math.abs(h2 - h1);
  if (diff > 180) {
    if (h1 < h2) {
      h1 += 360;
    } else {
      h2 += 360;
    }
  }
  const mixedH = (h1 * (1 - ratio) + h2 * ratio) % 360;

  // 混合饱和度（保持较高值以避免灰色）
  const mixedS = Math.max(hsl1.s, hsl2.s) * 0.9 + (hsl1.s * (1 - ratio) + hsl2.s * ratio) * 0.1;

  // 混合亮度
  const mixedL = hsl1.l * (1 - ratio) + hsl2.l * ratio;

  const mixedRgb = hslToRgb({ h: mixedH, s: mixedS, l: mixedL });
  return rgbToHex(mixedRgb);
}

/**
 * 检查颜色对比度是否满足可访问性要求
 * WCAG AA 标准要求对比度至少为 4.5:1
 */
export function checkContrast(color1: string, color2: string): boolean {
  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);
  const ratio = getContrastRatio(rgb1, rgb2);
  return ratio >= 4.5;
}

/**
 * 为低对比度颜色生成描边颜色
 */
export function getStrokeColor(color: string, background: string = '#ffffff'): string | null {
  if (checkContrast(color, background)) {
    return null; // 对比度足够，不需要描边
  }

  // 根据背景亮度决定描边颜色
  const bgRgb = hexToRgb(background);
  const bgLuminance = getRelativeLuminance(bgRgb);

  // 背景亮，用深色描边；背景暗，用浅色描边
  return bgLuminance > 0.5 ? '#000000' : '#ffffff';
}

/**
 * 颜色混合器类
 */
export class ColorMixer {
  private primaryColor: string;
  private secondaryColor: string;
  private backgroundColor: string;

  constructor(primaryColor: string, secondaryColor: string, backgroundColor: string = '#ffffff') {
    this.primaryColor = primaryColor;
    this.secondaryColor = secondaryColor;
    this.backgroundColor = backgroundColor;
  }

  /**
   * 获取混合颜色
   */
  getMixedColor(ratio: number = 0.5): string {
    return mixColors(this.primaryColor, this.secondaryColor, ratio);
  }

  /**
   * 获取主作者颜色的描边（如果需要）
   */
  getPrimaryStroke(): string | null {
    return getStrokeColor(this.primaryColor, this.backgroundColor);
  }

  /**
   * 获取副作者颜色的描边（如果需要）
   */
  getSecondaryStroke(): string | null {
    return getStrokeColor(this.secondaryColor, this.backgroundColor);
  }

  /**
   * 获取混合颜色的描边（如果需要）
   */
  getMixedStroke(ratio: number = 0.5): string | null {
    const mixedColor = this.getMixedColor(ratio);
    return getStrokeColor(mixedColor, this.backgroundColor);
  }

  /**
   * 检查两个作者颜色的对比度
   */
  checkAuthorsContrast(): boolean {
    return checkContrast(this.primaryColor, this.secondaryColor);
  }
}

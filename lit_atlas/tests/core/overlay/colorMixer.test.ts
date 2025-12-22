/**
 * ColorMixer 测试
 * 参考：@docs/design/overlay_mode_module_20251215.md
 */

import { mixColors, checkContrast, getStrokeColor, ColorMixer } from '../../../src/core/overlay/colorMixer';

describe('colorMixer', () => {
  describe('mixColors', () => {
    it('应该混合两个颜色', () => {
      const result = mixColors('#ff0000', '#0000ff', 0.5);
      expect(result).toMatch(/^#[0-9a-f]{6}$/i);
    });

    it('ratio=0 应该返回第一个颜色', () => {
      const result = mixColors('#ff0000', '#0000ff', 0);
      expect(result.toLowerCase()).toBe('#ff0000');
    });

    it('ratio=1 应该返回第二个颜色', () => {
      const result = mixColors('#ff0000', '#0000ff', 1);
      expect(result.toLowerCase()).toBe('#0000ff');
    });

    it('应该保持饱和度避免灰色', () => {
      const result = mixColors('#ff0000', '#00ff00', 0.5);
      // 混合后不应该是灰色（#808080附近）
      expect(result.toLowerCase()).not.toBe('#808080');
    });
  });

  describe('checkContrast', () => {
    it('黑白应该有高对比度', () => {
      expect(checkContrast('#000000', '#ffffff')).toBe(true);
    });

    it('相似颜色应该有低对比度', () => {
      expect(checkContrast('#333333', '#444444')).toBe(false);
    });

    it('应该满足 WCAG AA 标准 (4.5:1)', () => {
      expect(checkContrast('#2c3e50', '#ffffff')).toBe(true);
    });
  });

  describe('getStrokeColor', () => {
    it('高对比度时不需要描边', () => {
      expect(getStrokeColor('#000000', '#ffffff')).toBeNull();
    });

    it('低对比度时应该返回描边颜色', () => {
      const stroke = getStrokeColor('#cccccc', '#ffffff');
      expect(stroke).not.toBeNull();
      expect(stroke).toBe('#000000'); // 亮背景用深色描边
    });

    it('暗背景应该用浅色描边', () => {
      const stroke = getStrokeColor('#333333', '#000000');
      expect(stroke).toBe('#ffffff');
    });
  });

  describe('ColorMixer', () => {
    it('应该创建 ColorMixer 实例', () => {
      const mixer = new ColorMixer('#ff0000', '#0000ff');
      expect(mixer).toBeInstanceOf(ColorMixer);
    });

    it('应该获取混合颜色', () => {
      const mixer = new ColorMixer('#ff0000', '#0000ff');
      const mixed = mixer.getMixedColor(0.5);
      expect(mixed).toMatch(/^#[0-9a-f]{6}$/i);
    });

    it('应该检查作者颜色对比度', () => {
      const mixer = new ColorMixer('#ff0000', '#0000ff');
      const hasContrast = mixer.checkAuthorsContrast();
      expect(typeof hasContrast).toBe('boolean');
    });

    it('应该为低对比度颜色提供描边', () => {
      const mixer = new ColorMixer('#cccccc', '#dddddd', '#ffffff');
      const stroke = mixer.getPrimaryStroke();
      expect(stroke).not.toBeNull();
    });
  });
});

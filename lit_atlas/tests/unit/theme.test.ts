/**
 * UI 设计系统单元测试
 * 参考：@docs/design/ui_design_system_20251222.md
 */

import { THEME_COLORS, SPACING, NODE_SIZES, TYPOGRAPHY, EASING, DURATIONS } from '@/core/theme';

describe('UI Design System', () => {
  describe('Colors', () => {
    it('应该包含所有必需的颜色令牌', () => {
      expect(THEME_COLORS.paper).toBeDefined();
      expect(THEME_COLORS.ink).toBeDefined();
      expect(THEME_COLORS.interactive).toBeDefined();
      expect(THEME_COLORS.semantic).toBeDefined();
      expect(THEME_COLORS.authors).toBeDefined();
    });

    it('纸张颜色应该有明暗两种模式', () => {
      expect(THEME_COLORS.paper.light).toBe('#F5F5F0');
      expect(THEME_COLORS.paper.dark).toBe('#1a1a1a');
    });

    it('作者主题色应该包含预定义作者', () => {
      expect(THEME_COLORS.authors.murakami).toBe('#2C3E50');
      expect(THEME_COLORS.authors.marquez).toBe('#F4D03F');
      expect(THEME_COLORS.authors.kafka).toBe('#8B4513');
    });
  });

  describe('Spacing', () => {
    it('应该遵循 8px 基准网格', () => {
      expect(SPACING.xs).toBe('4px');
      expect(SPACING.sm).toBe('8px');
      expect(SPACING.md).toBe('16px');
      expect(SPACING.lg).toBe('24px');
      expect(SPACING.xl).toBe('32px');
      expect(SPACING.xxl).toBe('48px');
    });

    it('节点尺寸应该定义默认、悬停和呼吸状态', () => {
      expect(NODE_SIZES.default).toBe(8);
      expect(NODE_SIZES.hover).toBe(12);
      expect(NODE_SIZES.breathing).toBe(16);
    });
  });

  describe('Typography', () => {
    it('应该包含中文字体', () => {
      expect(TYPOGRAPHY.fontFamily.sans).toContain('Noto Sans SC');
    });

    it('字号应该从 xs 到 2xl', () => {
      expect(TYPOGRAPHY.fontSize.xs).toBe('12px');
      expect(TYPOGRAPHY.fontSize['2xl']).toBe('32px');
    });
  });

  describe('Animations', () => {
    it('应该定义所有动画曲线', () => {
      expect(EASING.inkGrowth).toBeDefined();
      expect(EASING.ripple).toBeDefined();
      expect(EASING.camera).toBeDefined();
      expect(EASING.ui).toBeDefined();
    });

    it('动画时长应该符合性能预算', () => {
      expect(DURATIONS.fast).toBe(150);
      expect(DURATIONS.normal).toBe(300);
      expect(DURATIONS.slow).toBe(600);
      expect(DURATIONS.narrative).toBe(1000);
    });
  });
});

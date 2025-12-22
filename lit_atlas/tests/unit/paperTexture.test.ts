/**
 * 纸张纹理模块单元测试
 */
import {
  PaperTextureType,
  PAPER_TEXTURES,
  DEFAULT_PAPER_TEXTURE,
  generatePaperTextureFilter,
  getPaperBackgroundStyle,
  generateInkFilters,
  PaperTextureConfig
} from '../../src/core/theme/paperTexture';

describe('纸张纹理', () => {
  describe('PAPER_TEXTURES', () => {
    it('应该包含所有纹理类型', () => {
      expect(PAPER_TEXTURES[PaperTextureType.SMOOTH]).toBeDefined();
      expect(PAPER_TEXTURES[PaperTextureType.ROUGH]).toBeDefined();
      expect(PAPER_TEXTURES[PaperTextureType.VINTAGE]).toBeDefined();
      expect(PAPER_TEXTURES[PaperTextureType.WATERCOLOR]).toBeDefined();
    });

    it('每个纹理应该有正确的属性', () => {
      Object.values(PAPER_TEXTURES).forEach((texture: PaperTextureConfig) => {
        expect(texture.type).toBeDefined();
        expect(texture.opacity).toBeGreaterThan(0);
        expect(texture.opacity).toBeLessThanOrEqual(1);
        expect(texture.scale).toBeGreaterThan(0);
        expect(texture.color).toMatch(/^#[0-9a-f]{6}$/i);
      });
    });
  });

  describe('generatePaperTextureFilter', () => {
    it('应该生成有效的 SVG 滤镜', () => {
      const filter = generatePaperTextureFilter(DEFAULT_PAPER_TEXTURE);
      
      expect(filter).toContain('<filter');
      expect(filter).toContain('</filter>');
      expect(filter).toContain('feTurbulence');
    });

    it('应该为不同纹理类型生成不同的滤镜', () => {
      const smoothFilter = generatePaperTextureFilter(PAPER_TEXTURES[PaperTextureType.SMOOTH]);
      const roughFilter = generatePaperTextureFilter(PAPER_TEXTURES[PaperTextureType.ROUGH]);
      
      expect(smoothFilter).not.toBe(roughFilter);
    });

    it('应该包含正确的滤镜 ID', () => {
      const vintageFilter = generatePaperTextureFilter(PAPER_TEXTURES[PaperTextureType.VINTAGE]);
      expect(vintageFilter).toContain('id="paper-texture-vintage"');
    });
  });

  describe('getPaperBackgroundStyle', () => {
    it('应该返回有效的 CSS 样式对象', () => {
      const style = getPaperBackgroundStyle(DEFAULT_PAPER_TEXTURE);
      
      expect(style.backgroundColor).toBeDefined();
      expect(style.backgroundImage).toBeDefined();
      expect(style.backgroundBlendMode).toBe('multiply');
    });

    it('应该使用配置的颜色', () => {
      const customConfig = {
        ...DEFAULT_PAPER_TEXTURE,
        color: '#ffffff'
      };
      
      const style = getPaperBackgroundStyle(customConfig);
      expect(style.backgroundColor).toBe('#ffffff');
    });

    it('应该包含径向渐变', () => {
      const style = getPaperBackgroundStyle(DEFAULT_PAPER_TEXTURE);
      expect(style.backgroundImage).toContain('radial-gradient');
    });
  });

  describe('generateInkFilters', () => {
    it('应该生成墨迹效果滤镜', () => {
      const filters = generateInkFilters();
      
      expect(filters).toContain('id="ink-blur"');
      expect(filters).toContain('id="ink-spread"');
      expect(filters).toContain('id="ink-edge"');
    });

    it('应该包含必要的滤镜元素', () => {
      const filters = generateInkFilters();
      
      expect(filters).toContain('feGaussianBlur');
      expect(filters).toContain('feColorMatrix');
      expect(filters).toContain('feMorphology');
    });
  });
});

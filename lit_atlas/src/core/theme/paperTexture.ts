/**
 * 纸张纹理主题模块
 * 提供墨迹与边界的纸张质感样式
 */

/**
 * 纸张纹理类型
 */
export enum PaperTextureType {
  SMOOTH = 'smooth',
  ROUGH = 'rough',
  VINTAGE = 'vintage',
  WATERCOLOR = 'watercolor'
}

/**
 * 纸张纹理配置
 */
export interface PaperTextureConfig {
  type: PaperTextureType;
  opacity: number;
  scale: number;
  color: string;
}

/**
 * 默认纸张纹理配置
 */
export const DEFAULT_PAPER_TEXTURE: PaperTextureConfig = {
  type: PaperTextureType.VINTAGE,
  opacity: 0.15,
  scale: 1,
  color: '#f5f1e8'
};

/**
 * 纸张纹理样式
 */
export const PAPER_TEXTURES: Record<PaperTextureType, PaperTextureConfig> = {
  [PaperTextureType.SMOOTH]: {
    type: PaperTextureType.SMOOTH,
    opacity: 0.05,
    scale: 1,
    color: '#ffffff'
  },
  [PaperTextureType.ROUGH]: {
    type: PaperTextureType.ROUGH,
    opacity: 0.2,
    scale: 1.5,
    color: '#f8f6f0'
  },
  [PaperTextureType.VINTAGE]: {
    type: PaperTextureType.VINTAGE,
    opacity: 0.15,
    scale: 1,
    color: '#f5f1e8'
  },
  [PaperTextureType.WATERCOLOR]: {
    type: PaperTextureType.WATERCOLOR,
    opacity: 0.25,
    scale: 2,
    color: '#faf8f3'
  }
};

/**
 * 生成纸张纹理 SVG 滤镜
 * @param config 纸张纹理配置
 * @returns SVG 滤镜定义
 */
export function generatePaperTextureFilter(config: PaperTextureConfig = DEFAULT_PAPER_TEXTURE): string {
  const { type, opacity, scale } = config;

  switch (type) {
    case PaperTextureType.SMOOTH:
      return `
        <filter id="paper-texture-smooth">
          <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" result="noise" />
          <feColorMatrix in="noise" type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="discrete" tableValues="0 ${opacity}" />
          </feComponentTransfer>
          <feBlend in="SourceGraphic" in2="noise" mode="multiply" />
        </filter>
      `;

    case PaperTextureType.ROUGH:
      return `
        <filter id="paper-texture-rough">
          <feTurbulence type="fractalNoise" baseFrequency="${0.5 * scale}" numOctaves="4" result="noise" />
          <feColorMatrix in="noise" type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="discrete" tableValues="0 ${opacity}" />
          </feComponentTransfer>
          <feBlend in="SourceGraphic" in2="noise" mode="multiply" />
        </filter>
      `;

    case PaperTextureType.VINTAGE:
      return `
        <filter id="paper-texture-vintage">
          <feTurbulence type="fractalNoise" baseFrequency="${0.6 * scale}" numOctaves="3" seed="2" result="noise" />
          <feColorMatrix in="noise" type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="table" tableValues="0 ${opacity * 0.5} ${opacity}" />
          </feComponentTransfer>
          <feGaussianBlur stdDeviation="0.5" />
          <feBlend in="SourceGraphic" in2="noise" mode="multiply" />
        </filter>
      `;

    case PaperTextureType.WATERCOLOR:
      return `
        <filter id="paper-texture-watercolor">
          <feTurbulence type="turbulence" baseFrequency="${0.3 * scale}" numOctaves="5" result="noise" />
          <feColorMatrix in="noise" type="saturate" values="0" />
          <feComponentTransfer>
            <feFuncA type="table" tableValues="0 ${opacity * 0.3} ${opacity * 0.7} ${opacity}" />
          </feComponentTransfer>
          <feGaussianBlur stdDeviation="1" />
          <feBlend in="SourceGraphic" in2="noise" mode="multiply" />
        </filter>
      `;

    default:
      return generatePaperTextureFilter(DEFAULT_PAPER_TEXTURE);
  }
}

/**
 * 获取纸张背景样式
 * @param config 纸张纹理配置
 * @returns CSS 样式对象
 */
export function getPaperBackgroundStyle(config: PaperTextureConfig = DEFAULT_PAPER_TEXTURE): React.CSSProperties {
  return {
    backgroundColor: config.color,
    backgroundImage: `
      radial-gradient(circle at 20% 50%, rgba(0,0,0,0.02) 0%, transparent 50%),
      radial-gradient(circle at 80% 80%, rgba(0,0,0,0.02) 0%, transparent 50%),
      radial-gradient(circle at 40% 20%, rgba(255,255,255,0.03) 0%, transparent 30%)
    `,
    backgroundBlendMode: 'multiply'
  };
}

/**
 * 墨迹效果样式
 */
export const INK_STYLES = {
  // 墨迹线条样式
  line: {
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    filter: 'url(#ink-blur)'
  },
  // 墨迹节点样式
  node: {
    filter: 'url(#ink-spread)'
  }
};

/**
 * 生成墨迹效果 SVG 滤镜
 * @returns SVG 滤镜定义
 */
export function generateInkFilters(): string {
  return `
    <!-- 墨迹模糊效果 -->
    <filter id="ink-blur">
      <feGaussianBlur in="SourceGraphic" stdDeviation="0.5" result="blur" />
      <feColorMatrix in="blur" type="matrix" values="
        1 0 0 0 0
        0 1 0 0 0
        0 0 1 0 0
        0 0 0 1.2 0
      " />
    </filter>

    <!-- 墨迹扩散效果 -->
    <filter id="ink-spread">
      <feMorphology operator="dilate" radius="0.5" />
      <feGaussianBlur stdDeviation="1" />
      <feColorMatrix type="matrix" values="
        1 0 0 0 0
        0 1 0 0 0
        0 0 1 0 0
        0 0 0 1.5 -0.2
      " />
    </filter>

    <!-- 墨迹边缘效果 -->
    <filter id="ink-edge">
      <feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="3" result="noise" />
      <feDisplacementMap in="SourceGraphic" in2="noise" scale="2" xChannelSelector="R" yChannelSelector="G" />
      <feGaussianBlur stdDeviation="0.3" />
    </filter>
  `;
}

/**
 * 图层管理模块
 * 定义底图、线条、节点等 SVG 图层顺序及混合模式
 */

// 图层类型定义
export enum LayerType {
  BASE_MAP = 'base-map',
  GRID = 'grid',
  INK_LINES = 'ink-lines',
  RIPPLE_NODES = 'ripple-nodes',
  OVERLAYS = 'overlays',
  TOOLTIPS = 'tooltips',
  CONTROLS = 'controls'
}

// 图层配置
export interface LayerConfig {
  type: LayerType;
  zIndex: number;
  mixBlendMode?: string;
  opacity?: number;
  visible: boolean;
  interactive: boolean;
}

// 默认图层配置
export const DEFAULT_LAYERS: Record<LayerType, LayerConfig> = {
  [LayerType.BASE_MAP]: {
    type: LayerType.BASE_MAP,
    zIndex: 0,
    mixBlendMode: 'normal',
    opacity: 1,
    visible: true,
    interactive: false
  },
  [LayerType.GRID]: {
    type: LayerType.GRID,
    zIndex: 1,
    mixBlendMode: 'normal',
    opacity: 0.3,
    visible: false, // 默认隐藏
    interactive: false
  },
  [LayerType.INK_LINES]: {
    type: LayerType.INK_LINES,
    zIndex: 10,
    mixBlendMode: 'multiply', // 支持叠加模式
    opacity: 0.8,
    visible: true,
    interactive: false
  },
  [LayerType.RIPPLE_NODES]: {
    type: LayerType.RIPPLE_NODES,
    zIndex: 20,
    mixBlendMode: 'multiply',
    opacity: 1,
    visible: true,
    interactive: true
  },
  [LayerType.OVERLAYS]: {
    type: LayerType.OVERLAYS,
    zIndex: 30,
    mixBlendMode: 'screen',
    opacity: 0.6,
    visible: true,
    interactive: false
  },
  [LayerType.TOOLTIPS]: {
    type: LayerType.TOOLTIPS,
    zIndex: 40,
    mixBlendMode: 'normal',
    opacity: 1,
    visible: true,
    interactive: true
  },
  [LayerType.CONTROLS]: {
    type: LayerType.CONTROLS,
    zIndex: 50,
    mixBlendMode: 'normal',
    opacity: 1,
    visible: true,
    interactive: true
  }
};

// 图层顺序（用于排序）
export const LAYER_ORDER = [
  LayerType.BASE_MAP,
  LayerType.GRID,
  LayerType.INK_LINES,
  LayerType.RIPPLE_NODES,
  LayerType.OVERLAYS,
  LayerType.TOOLTIPS,
  LayerType.CONTROLS
];

/**
 * 叠加模式枚举
 */
export enum BlendMode {
  NORMAL = 'normal',
  MULTIPLY = 'multiply',
  SCREEN = 'screen',
  OVERLAY = 'overlay',
  SOFT_LIGHT = 'soft-light',
  HARD_LIGHT = 'hard-light',
  COLOR_DODGE = 'color-dodge',
  COLOR_BURN = 'color-burn',
  DARKEN = 'darken',
  LIGHTEN = 'lighten',
  DIFFERENCE = 'difference',
  EXCLUSION = 'exclusion',
  HUE = 'hue',
  SATURATION = 'saturation',
  COLOR = 'color',
  LUMINOSITY = 'luminosity'
}

/**
 * 获取适合的颜色混合模式
 * @param mode 混合模式名称
 * @returns CSS混合模式字符串
 */
export function getBlendMode(mode: BlendMode): string {
  return `mix-blend-mode: ${mode}`;
}

/**
 * 图层性能优化配置
 */
export interface LayerPerformanceConfig {
  enableHardwareAcceleration: boolean;
  enableLayerOptimization: boolean;
  reduceAnimations: boolean;
  maxVisibleLayers: number;
}

/**
 * 默认性能配置
 */
export const DEFAULT_PERFORMANCE_CONFIG: LayerPerformanceConfig = {
  enableHardwareAcceleration: true,
  enableLayerOptimization: true,
  reduceAnimations: false,
  maxVisibleLayers: 7
};

/**
 * 检查是否启用低性能模式
 * @returns 是否为低性能模式
 */
export function isLowPerformanceMode(): boolean {
  // 检查 prefers-reduced-motion
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
  return false;
}

/**
 * 获取优化后的图层配置
 * @param layers 原始图层配置
 * @param performanceConfig 性能配置
 * @returns 优化后的图层配置
 */
export function optimizeLayers(
  layers: Record<LayerType, LayerConfig>,
  performanceConfig: LayerPerformanceConfig = DEFAULT_PERFORMANCE_CONFIG
): Record<LayerType, LayerConfig> {
  const optimized = { ...layers };
  
  // 如果启用低性能模式，减少动画
  if (isLowPerformanceMode() || performanceConfig.reduceAnimations) {
    // 降低不透明度和关闭复杂混合
    Object.keys(optimized).forEach(key => {
      const layer = optimized[key as LayerType];
      if (layer.opacity) {
        layer.opacity = Math.min(layer.opacity, 0.7);
      }
      if (layer.mixBlendMode && layer.mixBlendMode !== 'normal') {
        layer.mixBlendMode = 'normal';
      }
    });
  }
  
  // 硬件加速优化
  if (performanceConfig.enableHardwareAcceleration) {
    // 为重要图层启用硬件加速
    const acceleratedLayers = [
      LayerType.INK_LINES,
      LayerType.RIPPLE_NODES,
      LayerType.TOOLTIPS
    ];
    
    acceleratedLayers.forEach(layerType => {
      if (optimized[layerType]) {
        // 这里可以添加 will-change CSS 属性
        console.debug(`为图层 ${layerType} 启用硬件加速`);
      }
    });
  }
  
  return optimized;
}
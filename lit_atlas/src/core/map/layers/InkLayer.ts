/**
 * 墨迹渲染层 - 自定义 Canvas 渲染实现
 * 
 * 功能：
 * - 墨迹生长路径（Variable Stroke Growth）
 * - 叙事涟漪节点（Narrative Ripples）
 * - 路径流动特效（Flowing Pulse）
 */

import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { Style, Stroke, Circle, Fill } from 'ol/style';
import type { FeatureLike } from 'ol/Feature';
import type Feature from 'ol/Feature';
import type { Coordinate } from 'ol/coordinate';
import LineString from 'ol/geom/LineString';
import Point from 'ol/geom/Point';

import { THEME_COLORS } from '../../theme/colors';
import { AnimationController, AnimationState } from '../animation/AnimationController';

/**
 * 墨迹层配置
 */
export interface InkLayerConfig {
  /** 动画控制器 */
  animationController: AnimationController;
  /** 是否启用动画 */
  enableAnimation?: boolean;
}

/**
 * 创建墨迹渲染层
 */
export function createInkLayer(
  source: VectorSource,
  config: InkLayerConfig
): VectorLayer<VectorSource> {
  const layer = new VectorLayer({
    source,
    style: (feature) => createInkStyle(feature, config)
  });

  // 注册 postrender 钩子用于高级动画
  if (config.enableAnimation) {
    layer.on('postrender', (event) => {
      renderInkAnimations(event, config);
    });
  }

  return layer;
}

/**
 * 创建墨迹样式
 */
function createInkStyle(
  feature: FeatureLike,
  config: InkLayerConfig
): Style | Style[] {
  if (!feature || !('get' in feature)) {
    return new Style();
  }

  const featureType = feature.get('type');
  const animController = config.animationController;
  const state = animController.calculateFeatureState(feature as Feature);
  const progress = animController.calculateProgress(feature as Feature);

  // 路线样式
  if (featureType === 'route') {
    return createRouteStyle(feature, state, progress);
  }

  // 城市节点样式
  if (featureType === 'city') {
    return createCityStyle(feature, state, progress);
  }

  return new Style();
}

/**
 * 创建路线样式 - 墨迹生长效果
 */
function createRouteStyle(
  feature: FeatureLike,
  state: AnimationState,
  progress: number
): Style {
  const geometry = feature.getGeometry();
  
  if (!(geometry instanceof LineString)) {
    return new Style();
  }

  // 根据状态选择颜色
  let color: string;
  let width: number;
  let opacity: number;

  switch (state) {
    case AnimationState.GROWING:
      // 生长中 - 朱砂色
      color = THEME_COLORS.traditional.cinnabar;
      width = 2 + progress * 2; // 动态线宽
      opacity = 0.6 + progress * 0.4;
      break;

    case AnimationState.ACTIVE:
      // 常亮 - 黛蓝色
      color = THEME_COLORS.traditional.indigo;
      width = 2;
      opacity = 0.6;
      break;

    default:
      // 隐藏
      return new Style();
  }

  // 创建样式
  const style = new Style({
    stroke: new Stroke({
      color: `rgba(${hexToRgb(color)}, ${opacity})`,
      width,
      lineCap: 'round',
      lineJoin: 'round'
    })
  });

  // 生长动画：裁剪几何体
  if (state === AnimationState.GROWING && progress < 1) {
    const coords = geometry.getCoordinates();
    const totalLength = coords.length;
    const visibleLength = Math.floor(totalLength * progress);
    
    if (visibleLength > 1) {
      const partialCoords = coords.slice(0, visibleLength);
      const partialGeometry = new LineString(partialCoords);
      style.setGeometry(partialGeometry);
    }
  }

  return style;
}

/**
 * 创建城市节点样式 - 涟漪效果
 */
function createCityStyle(
  feature: FeatureLike,
  state: AnimationState,
  progress: number
): Style[] {
  const routeCount = feature.get('routeCount') || 1;
  const baseRadius = Math.min(6 + routeCount * 2, 16);

  const styles: Style[] = [];

  // 主节点
  const mainStyle = new Style({
    image: new Circle({
      radius: baseRadius,
      fill: new Fill({
        color: state === AnimationState.GROWING 
          ? THEME_COLORS.traditional.cinnabar
          : THEME_COLORS.traditional.indigo
      }),
      stroke: new Stroke({
        color: '#ffffff',
        width: 2
      })
    })
  });

  styles.push(mainStyle);

  // 涟漪效果
  if (state === AnimationState.RIPPLING) {
    const rippleStyles = createRippleStyles(baseRadius, progress);
    styles.push(...rippleStyles);
  }

  // 呼吸灯效果（常亮状态）
  if (state === AnimationState.ACTIVE) {
    const breathProgress = (Math.sin(Date.now() / 1000) + 1) / 2;
    const glowStyle = new Style({
      image: new Circle({
        radius: baseRadius + 4,
        fill: new Fill({
          color: `rgba(69, 123, 157, ${0.2 * breathProgress})` // 松石色光晕
        })
      })
    });
    styles.push(glowStyle);
  }

  return styles;
}

/**
 * 创建涟漪样式（多层扩散）
 */
function createRippleStyles(baseRadius: number, progress: number): Style[] {
  const ripples: Style[] = [];
  const rippleCount = 3;

  for (let i = 0; i < rippleCount; i++) {
    const delay = i * 0.2;
    const rippleProgress = Math.max(0, Math.min(1, (progress - delay) / (1 - delay)));
    
    if (rippleProgress > 0) {
      const radius = baseRadius + rippleProgress * 20;
      const opacity = (1 - rippleProgress) * 0.4;

      ripples.push(new Style({
        image: new Circle({
          radius,
          stroke: new Stroke({
            color: `rgba(69, 123, 157, ${opacity})`, // 松石色
            width: 2
          })
        })
      }));
    }
  }

  return ripples;
}

/**
 * 渲染高级动画效果（postrender 钩子）
 */
function renderInkAnimations(
  event: any,
  config: InkLayerConfig
): void {
  const context = event.context as CanvasRenderingContext2D;
  const frameState = event.frameState;
  
  if (!context || !frameState) {
    return;
  }

  // 这里可以添加更复杂的 Canvas 动画
  // 例如：路径流动粒子、墨迹渗透效果等
  
  // 持续请求重绘以保持动画循环
  frameState.animate = true;
}

/**
 * 工具函数：十六进制转 RGB
 */
function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r}, ${g}, ${b}`;
}

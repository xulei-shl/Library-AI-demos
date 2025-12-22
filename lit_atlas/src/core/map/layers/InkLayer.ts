/**
 * 墨迹渲染层 - 自定义 Canvas 渲染实现
 * v0.4.0: 完整实现墨迹生长、涟漪与粒子效果
 */

import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import { Style, Stroke, Circle, Fill } from 'ol/style';
import type { FeatureLike } from 'ol/Feature';
import type Feature from 'ol/Feature';
import LineString from 'ol/geom/LineString';
import Point from 'ol/geom/Point';
import { getVectorContext } from 'ol/render';
import { toLonLat } from 'ol/proj';

import { THEME_COLORS, colorUtils } from '../../theme/colors';
import { AnimationController, AnimationState } from '../animation/AnimationController';

export interface InkLayerConfig {
  animationController: AnimationController;
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
    // 基础样式：对于非动画状态或静态层，提供回退样式
    style: (feature) => {
      // 动画期间，我们主要依靠 postrender 绘制，这里只返回简单的静态样式或空样式
      // 为了性能，我们可以让 OpenLayers 处理静态的“历史”路径
      const state = config.animationController.calculateFeatureState(feature as Feature);
      if (state === AnimationState.HIDDEN) return new Style();

      // 如果是完全展示状态，也可以用标准样式（为了清晰度），但为了风格统一，
      // 我们这里选择全部在 postrender 中绘制，或者只让 OL 绘制最基础的线
      return new Style(); // 全部交给 postrender
    },
    updateWhileAnimating: true,
    updateWhileInteracting: true,
  });

  // 注册 postrender 钩子用于高级动画
  let renderCount = 0;
  layer.on('postrender', (event) => {
    renderCount++;
    if (renderCount === 1 || renderCount % 60 === 0) {
      console.info('[InkLayer] postrender 触发', { renderCount, hasEvent: !!event });
    }
    renderInkAnimations(event, source, config);
  });

  return layer;
}

/**
 * 渲染墨迹动画核心逻辑
 */
function renderInkAnimations(
  event: any,
  source: VectorSource,
  config: InkLayerConfig
) {
  const context = event.context as CanvasRenderingContext2D;
  const vectorContext = getVectorContext(event);
  const frameState = event.frameState;
  const animController = config.animationController;

  if (!context || !frameState) return;

  if (config.enableAnimation) {
    animController.syncWithFrameTime(frameState.time);
  }

  // 保存上下文状态
  context.save();

  // 1. 设置墨迹混合模式
  context.globalCompositeOperation = 'source-over'; // 使用默认混合避免透明叠加导致画面消失
  context.lineCap = 'round';
  context.lineJoin = 'round';

  const features = source.getFeatures();
  const pixelRatio = frameState.pixelRatio;

  // 强制输出前几帧的调试信息
  const currentTime = animController.getTime();
  const shouldLog = currentTime < 5000; // 前5秒强制输出

  if (shouldLog || Math.random() < 0.01) {
    const stateBreakdown = features.reduce((acc, f) => {
      const state = animController.calculateFeatureState(f);
      const type = f.get('type');
      const key = `${type}-${state}`;
      acc[key] = (acc[key] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    console.debug('[InkLayer] Rendering frame', { 
      featureCount: features.length,
      currentTime,
      hasContext: !!context,
      hasVectorContext: !!vectorContext,
      stateBreakdown
    });
  }

  features.forEach(feature => {
    const state = animController.calculateFeatureState(feature);
    const progress = animController.calculateProgress(feature);
    const type = feature.get('type');

    if (state === AnimationState.HIDDEN) return;



    if (type === 'route') {
      renderRoute(context, vectorContext, feature, state, progress, pixelRatio);
    } else if (type === 'city') {
      renderCity(context, vectorContext, feature, state, progress, pixelRatio);
    } else if (type === 'ripple') {
      renderRipple(context, vectorContext, feature, state, progress, pixelRatio);
    }
  });

  context.restore();

  // 持续请求重绘以保持动画循环
  if (config.enableAnimation) {
    frameState.animate = true;
  }
}

/**
 * 绘制路线
 */
function renderRoute(
  ctx: CanvasRenderingContext2D,
  vectorContext: any,
  feature: Feature,
  state: AnimationState,
  progress: number,
  pixelRatio: number
) {
  const geometry = feature.getGeometry();
  if (!(geometry instanceof LineString)) return;

  const color = state === AnimationState.GROWING
    ? THEME_COLORS.traditional.cinnabar
    : THEME_COLORS.traditional.indigo;

  // 基础线宽
  const baseWidth = 3 * pixelRatio;

  // 1. 绘制墨迹路径
  ctx.beginPath();

  let renderGeometry = geometry;

  if (state === AnimationState.GROWING && progress < 1) {
    const coords = geometry.getCoordinates();
    if (coords.length < 2) {
      return;
    }

    // 允许最短路线（仅起终点）也可渐进绘制
    const totalSegments = coords.length - 1;
    const clampedProgress = Math.max(0.0001, progress);
    const scaled = clampedProgress * totalSegments;
    const baseIndex = Math.min(Math.floor(scaled), totalSegments - 1);
    const remainder = scaled - baseIndex;

    const startPoint = coords[baseIndex];
    const endPoint = coords[Math.min(baseIndex + 1, coords.length - 1)];
    if (!startPoint || !endPoint) {
      return;
    }

    const partialCoords = coords.slice(0, baseIndex + 1);
    const interpolatedX = startPoint[0] + (endPoint[0] - startPoint[0]) * remainder;
    const interpolatedY = startPoint[1] + (endPoint[1] - startPoint[1]) * remainder;
    partialCoords.push([interpolatedX, interpolatedY]);

    renderGeometry = new LineString(partialCoords);
  }

  const inkStyle = new Style({
    stroke: new Stroke({
      color: colorUtils.hexToRgba(color, 0.8),
      width: baseWidth,
      lineCap: 'round',
      lineJoin: 'round',
    })
  });

  // 模拟墨迹晕染
  ctx.shadowBlur = 4 * pixelRatio;
  ctx.shadowColor = colorUtils.hexToRgba(color, 0.4);

  vectorContext.setStyle(inkStyle);
  vectorContext.drawGeometry(renderGeometry);

  ctx.shadowBlur = 0; // 重置

  // 2. 绘制流动粒子 (Flowing Pulse) - 仅在 Active 状态
  if (state === AnimationState.ACTIVE) {
    const length = geometry.getLength();
    if (length > 0) {
      const time = Date.now() / 1000;
      const speed = 0.2; // 速度
      const particlePos = (time * speed) % 1;
      const coord = geometry.getCoordinateAt(particlePos);

      const particleStyle = new Style({
        image: new Circle({
          radius: 2 * pixelRatio,
          fill: new Fill({ color: '#ffffff' }),
          stroke: new Stroke({ color: color, width: 1 })
        })
      });

      vectorContext.setStyle(particleStyle);
      vectorContext.drawGeometry(new Point(coord));
    }
  }
}

/**
 * 绘制城市节点 (静态)
 */
function renderCity(
  ctx: CanvasRenderingContext2D,
  vectorContext: any,
  feature: Feature,
  state: AnimationState,
  progress: number,
  pixelRatio: number
) {
  const geometry = feature.getGeometry();
  if (!(geometry instanceof Point)) return;

  // 城市总是显示为白色小点
  const pointStyle = new Style({
    image: new Circle({
      radius: 3 * pixelRatio,
      fill: new Fill({ color: '#FFFFFF' }),
      stroke: new Stroke({ color: '#666666', width: 1 * pixelRatio })
    })
  });

  vectorContext.setStyle(pointStyle);
  vectorContext.drawGeometry(geometry);
}

/**
 * 绘制涟漪 (动态)
 */
function renderRipple(
  ctx: CanvasRenderingContext2D,
  vectorContext: any,
  feature: Feature,
  state: AnimationState,
  progress: number,
  pixelRatio: number
) {
  const geometry = feature.getGeometry();
  if (!(geometry instanceof Point)) return;

  // 仅在 RIPPLING 状态下绘制
  // 或者在 GROWING 状态下也可以绘制？
  // AnimationController 逻辑：GROWING -> RIPPLING -> ACTIVE
  // 对于 RippleFeature，我们设置 duration = RIPPLE_DURATION
  // 所以它可能直接进入 GROWING 状态 (如果 duration 是 growthDuration)
  // 但我们在 OpenLayersMap 中设置 RippleFeature 的 duration 是 RIPPLE_DURATION
  // AnimationController 的 calculateFeatureState 逻辑是：
  // elapsed < growthDuration -> GROWING
  // elapsed < growthDuration + rippleDuration -> RIPPLING
  // 
  // 我们的 RippleFeature 不需要 "GROWING" 阶段，或者 "GROWING" 就是涟漪扩散阶段。
  // 让我们看看 AnimationController 的逻辑。
  // AnimationController 的 config.growthDuration 是全局配置。
  // 这有点问题。AnimationController 假设所有 Feature 都有相同的阶段。
  // 
  // 修正：AnimationController 的 calculateFeatureState 使用全局 config.growthDuration。
  // 这意味着 RippleFeature 也会有 "GROWING" 阶段。
  // 如果 RippleFeature 的 duration (注册时) 只是用来判断是否 ACTIVE?
  // 不，AnimationController 的 registerFeature 接受 duration，但 calculateFeatureState 忽略它，只用 config。
  // 这是一个设计缺陷。
  // 
  // 临时解决方案：
  // 在 renderRipple 中，利用 progress (0-1) 来绘制涟漪。
  // 不管 state 是 GROWING 还是 RIPPLING，只要 progress < 1，就绘制。
  // 
  // 实际上，AnimationController 的 calculateProgress 会根据 state 返回 0-1。
  // 如果 state 是 GROWING，progress 是 0-1。
  // 如果 state 是 RIPPLING，progress 是 0-1。
  // 
  // 我们就利用 progress 来控制半径。

  const color = THEME_COLORS.traditional.turquoise;
  const maxRadius = 25 * pixelRatio;

  // 绘制多层涟漪
  const rippleCount = 3;

  // 使用 progress (0-1)
  // 假设整个生命周期都是涟漪
  // 如果 state 是 ACTIVE，说明涟漪结束了，不绘制
  if (state === AnimationState.ACTIVE) return;

  // 这里的 progress 是根据 state 计算的。
  // 如果是 GROWING，progress 0->1
  // 如果是 RIPPLING，progress 0->1
  // 我们希望涟漪是一个连续的过程。
  // 简单起见，我们只在 GROWING 阶段绘制涟漪 (因为 RippleFeature 的 duration 对应 growthDuration?)
  // 不，OpenLayersMap 中：
  // RippleFeature: duration = RIPPLE_DURATION
  // AnimationController: growthDuration = 2000
  // 所以 RippleFeature 会经历 2000ms 的 GROWING。
  // 然后进入 RIPPLING (1500ms)。
  // 
  // 我们就在 GROWING 和 RIPPLING 阶段都绘制。
  // 为了平滑，我们可以重新计算一个 "global ripple progress"。
  // 或者简单点，只在 GROWING 阶段绘制，因为那是主要持续时间。

  if (state === AnimationState.GROWING || state === AnimationState.RIPPLING) {
    // 重新计算一个基于时间的 progress，忽略 state 的分段
    // 实际上很难获取原始 elapsed。
    // 
    // 让我们只利用 GROWING 阶段。
    // 在 OpenLayersMap 中，我们设置 RippleFeature 的 duration = RIPPLE_DURATION (2000ms)。
    // 这正好匹配 AnimationController 的 default growthDuration (2000ms)。
    // 所以 RippleFeature 会在 GROWING 阶段度过它的生命周期。

    for (let i = 0; i < rippleCount; i++) {
      const delay = i * 0.2;
      const rippleProgress = (progress - delay) / (1 - delay);

      if (rippleProgress > 0 && rippleProgress < 1) {
        const radius = 2 * pixelRatio + rippleProgress * (maxRadius - 2 * pixelRatio);
        const opacity = (1 - rippleProgress) * 0.8;

        const rippleStyle = new Style({
          image: new Circle({
            radius: radius,
            stroke: new Stroke({
              color: colorUtils.hexToRgba(color, opacity),
              width: 1.5 * pixelRatio
            })
          })
        });

        vectorContext.setStyle(rippleStyle);
        vectorContext.drawGeometry(geometry);
      }
    }
  }
}

/**
 * 动画调度器 - 管理地图动画的全局时间轴
 * 
 * 职责：
 * - 管理全局动画时间
 * - 计算 Feature 的动画状态（生长/常亮/隐藏）
 * - 提供帧循环驱动的动画更新
 */

import type Feature from 'ol/Feature';

/**
 * Feature 动画状态
 */
export enum AnimationState {
  HIDDEN = 'hidden',      // 未开始
  GROWING = 'growing',    // 生长中
  RIPPLING = 'rippling',  // 涟漪扩散
  ACTIVE = 'active',      // 常亮状态
  FADING = 'fading'       // 淡出
}

/**
 * 动画配置
 */
export interface AnimationConfig {
  /** 生长动画持续时间（毫秒） */
  growthDuration: number;
  /** 涟漪动画持续时间（毫秒） */
  rippleDuration: number;
  /** 流动动画速度 */
  flowSpeed: number;
}

/**
 * Feature 动画元数据
 */
export interface FeatureAnimationMeta {
  /** 开始时间（相对时间轴） */
  startTime: number;
  /** 持续时间 */
  duration: number;
  /** 当前状态 */
  state: AnimationState;
  /** 动画进度 (0-1) */
  progress: number;
}

/**
 * 动画调度器
 */
export class AnimationController {
  private currentTime: number = 0;
  private isPlaying: boolean = false;
  private animationFrameId: number | null = null;
  private lastFrameTime: number = 0;
  
  private config: AnimationConfig = {
    growthDuration: 2000,
    rippleDuration: 1500,
    flowSpeed: 0.5
  };

  private featureMetaMap = new WeakMap<Feature, FeatureAnimationMeta>();
  private updateCallbacks: Set<() => void> = new Set();

  constructor(config?: Partial<AnimationConfig>) {
    if (config) {
      this.config = { ...this.config, ...config };
    }
  }

  /**
   * 注册 Feature 的动画元数据
   */
  registerFeature(feature: Feature, startTime: number, duration: number): void {
    this.featureMetaMap.set(feature, {
      startTime,
      duration,
      state: AnimationState.HIDDEN,
      progress: 0
    });
  }

  /**
   * 获取 Feature 的动画元数据
   */
  getFeatureMeta(feature: Feature): FeatureAnimationMeta | undefined {
    return this.featureMetaMap.get(feature);
  }

  /**
   * 计算 Feature 的当前动画状态
   */
  calculateFeatureState(feature: Feature): AnimationState {
    const meta = this.featureMetaMap.get(feature);
    if (!meta) {
      return AnimationState.HIDDEN;
    }

    const elapsed = this.currentTime - meta.startTime;

    if (elapsed < 0) {
      return AnimationState.HIDDEN;
    }

    if (elapsed < this.config.growthDuration) {
      return AnimationState.GROWING;
    }

    if (elapsed < this.config.growthDuration + this.config.rippleDuration) {
      return AnimationState.RIPPLING;
    }

    return AnimationState.ACTIVE;
  }

  /**
   * 计算动画进度 (0-1)
   */
  calculateProgress(feature: Feature): number {
    const meta = this.featureMetaMap.get(feature);
    if (!meta) {
      return 0;
    }

    const state = this.calculateFeatureState(feature);
    const elapsed = this.currentTime - meta.startTime;

    switch (state) {
      case AnimationState.GROWING:
        return Math.min(elapsed / this.config.growthDuration, 1);
      
      case AnimationState.RIPPLING:
        const rippleElapsed = elapsed - this.config.growthDuration;
        return Math.min(rippleElapsed / this.config.rippleDuration, 1);
      
      case AnimationState.ACTIVE:
        return 1;
      
      default:
        return 0;
    }
  }

  /**
   * 启动动画循环
   */
  play(): void {
    if (this.isPlaying) {
      return;
    }

    this.isPlaying = true;
    this.lastFrameTime = performance.now();
    this.tick();
  }

  /**
   * 暂停动画
   */
  pause(): void {
    this.isPlaying = false;
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  /**
   * 设置当前时间
   */
  setTime(time: number): void {
    this.currentTime = time;
    this.notifyUpdate();
  }

  /**
   * 获取当前时间
   */
  getTime(): number {
    return this.currentTime;
  }

  /**
   * 注册更新回调
   */
  onUpdate(callback: () => void): () => void {
    this.updateCallbacks.add(callback);
    return () => this.updateCallbacks.delete(callback);
  }

  /**
   * 帧循环
   */
  private tick = (): void => {
    if (!this.isPlaying) {
      return;
    }

    const now = performance.now();
    const delta = now - this.lastFrameTime;
    this.lastFrameTime = now;

    // 更新时间（可以根据播放速度调整）
    this.currentTime += delta;

    // 通知所有监听器
    this.notifyUpdate();

    // 请求下一帧
    this.animationFrameId = requestAnimationFrame(this.tick);
  };

  /**
   * 通知更新
   */
  private notifyUpdate(): void {
    this.updateCallbacks.forEach(callback => callback());
  }

  /**
   * 销毁
   */
  destroy(): void {
    this.pause();
    this.updateCallbacks.clear();
    this.featureMetaMap = new WeakMap();
  }
}

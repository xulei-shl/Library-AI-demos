/**
 * 性能优化工具
 * 参考：@docs/design/performance_budget_20251222.md
 */

/**
 * 检测低性能设备
 */
export function isLowPerformanceDevice(): boolean {
  // 检查 CPU 核心数
  const cores = navigator.hardwareConcurrency || 4;
  
  // 检查是否为移动设备
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(
    navigator.userAgent
  );
  
  // 检查内存（如果可用）
  const memory = (navigator as any).deviceMemory;
  const hasLowMemory = memory && memory < 4;
  
  return cores < 4 || (isMobile && hasLowMemory);
}

/**
 * 检测用户是否偏好减少动画
 */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * 性能配置
 */
export interface PerformanceConfig {
  // 是否启用阴影
  enableShadows: boolean;
  // 动画速度倍数
  animationSpeedMultiplier: number;
  // 曲线插值点数
  curveInterpolationPoints: number;
  // 是否启用虚拟化
  enableVirtualization: boolean;
  // 虚拟化阈值
  virtualizationThreshold: number;
  // 是否启用 GPU 加速
  enableGPUAcceleration: boolean;
}

/**
 * 获取性能配置
 */
export function getPerformanceConfig(): PerformanceConfig {
  const isLowPerf = isLowPerformanceDevice();
  const reducedMotion = prefersReducedMotion();

  return {
    enableShadows: !isLowPerf,
    animationSpeedMultiplier: reducedMotion ? 0.1 : isLowPerf ? 0.5 : 1,
    curveInterpolationPoints: isLowPerf ? 20 : 50,
    enableVirtualization: isLowPerf,
    virtualizationThreshold: isLowPerf ? 100 : 200,
    enableGPUAcceleration: !isLowPerf,
  };
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;
  return function (this: any, ...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;
  return function (this: any, ...args: Parameters<T>) {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

/**
 * 请求空闲回调（兼容性包装）
 */
export function requestIdleCallback(
  callback: () => void,
  options?: { timeout?: number }
): number {
  if (typeof window === 'undefined') {
    return 0;
  }
  
  if ('requestIdleCallback' in window) {
    return (window as any).requestIdleCallback(callback, options);
  }
  
  // Fallback to setTimeout
  return setTimeout(callback, 1) as unknown as number;
}

/**
 * 取消空闲回调
 */
export function cancelIdleCallback(id: number): void {
  if (typeof window === 'undefined') {
    return;
  }
  
  if ('cancelIdleCallback' in window) {
    (window as any).cancelIdleCallback(id);
  } else {
    clearTimeout(id);
  }
}

/**
 * 批量更新（使用 RAF）
 */
export class BatchUpdater {
  private pending: Set<() => void> = new Set();
  private rafId: number | null = null;

  schedule(callback: () => void): void {
    this.pending.add(callback);
    
    if (!this.rafId) {
      this.rafId = requestAnimationFrame(() => {
        this.flush();
      });
    }
  }

  private flush(): void {
    const callbacks = Array.from(this.pending);
    this.pending.clear();
    this.rafId = null;
    
    callbacks.forEach((cb) => cb());
  }

  cancel(): void {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.pending.clear();
  }
}

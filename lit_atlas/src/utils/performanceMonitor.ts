/**
 * 运行时性能监控工具
 * 参考：@docs/design/performance_budget_20251222.md
 */

/**
 * 性能标记管理器
 */
export class PerformanceMonitor {
  private marks: Map<string, number> = new Map();

  /**
   * 开始计时
   */
  start(label: string): void {
    if (typeof performance === 'undefined') return;
    this.marks.set(label, performance.now());
    performance.mark(`${label}-start`);
  }

  /**
   * 结束计时并返回耗时（毫秒）
   */
  end(label: string): number {
    if (typeof performance === 'undefined') return 0;

    const startTime = this.marks.get(label);
    if (!startTime) {
      console.warn(`[PerformanceMonitor] 未找到标记: ${label}`);
      return 0;
    }

    const endTime = performance.now();
    const duration = endTime - startTime;

    performance.mark(`${label}-end`);
    performance.measure(label, `${label}-start`, `${label}-end`);

    this.marks.delete(label);
    return duration;
  }

  /**
   * 记录并输出耗时
   */
  log(label: string, threshold?: number): number {
    const duration = this.end(label);

    if (threshold && duration > threshold) {
      console.warn(
        `[性能警告] ${label}: ${duration.toFixed(2)}ms (阈值: ${threshold}ms)`,
      );
    } else {
      console.log(`[性能] ${label}: ${duration.toFixed(2)}ms`);
    }

    return duration;
  }

  /**
   * 获取所有性能指标
   */
  getMetrics(): PerformanceEntry[] {
    if (typeof performance === 'undefined') return [];
    return performance.getEntriesByType('measure');
  }

  /**
   * 清除所有标记
   */
  clear(): void {
    if (typeof performance === 'undefined') return;
    this.marks.clear();
    performance.clearMarks();
    performance.clearMeasures();
  }
}

/**
 * 全局单例
 */
export const perfMonitor = new PerformanceMonitor();

/**
 * 监控函数执行时间的装饰器
 */
export function measurePerformance(threshold?: number) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor,
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: unknown[]) {
      const className = target?.constructor?.name || 'Unknown';
      const label = `${className}.${propertyKey}`;
      perfMonitor.start(label);

      try {
        const result = await originalMethod.apply(this, args);
        perfMonitor.log(label, threshold);
        return result;
      } catch (error) {
        perfMonitor.end(label);
        throw error;
      }
    };

    return descriptor;
  };
}

/**
 * 检测低性能设备
 */
export function isLowPerformanceDevice(): boolean {
  if (typeof navigator === 'undefined') return false;

  const cores = navigator.hardwareConcurrency || 4;
  const isMobile =
    /Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent);

  return cores < 4 || isMobile;
}

/**
 * 检测用户是否偏好减少动画
 */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * 内存使用监控（仅 Chrome）
 */
export function getMemoryUsage(): {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
} | null {
  if (typeof performance === 'undefined' || !(performance as unknown as { memory?: unknown }).memory) {
    return null;
  }

  const memory = (performance as unknown as { memory: { usedJSHeapSize: number; totalJSHeapSize: number; jsHeapSizeLimit: number } }).memory;
  return {
    usedJSHeapSize: memory.usedJSHeapSize,
    totalJSHeapSize: memory.totalJSHeapSize,
    jsHeapSizeLimit: memory.jsHeapSizeLimit,
  };
}

/**
 * 帧率监控
 */
export class FPSMonitor {
  private frames: number[] = [];
  private lastTime = 0;
  private rafId: number | null = null;

  start(): void {
    this.lastTime = performance.now();
    this.tick();
  }

  private tick = (): void => {
    const now = performance.now();
    const delta = now - this.lastTime;
    this.lastTime = now;

    const fps = 1000 / delta;
    this.frames.push(fps);

    // 保留最近 60 帧
    if (this.frames.length > 60) {
      this.frames.shift();
    }

    this.rafId = requestAnimationFrame(this.tick);
  };

  getAverageFPS(): number {
    if (this.frames.length === 0) return 0;
    const sum = this.frames.reduce((a, b) => a + b, 0);
    return sum / this.frames.length;
  }

  stop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }
}

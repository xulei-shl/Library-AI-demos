/**
 * 内存监控工具
 * 参考：@docs/design/performance_budget_20251222.md
 */

interface MemoryInfo {
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
}

/**
 * 获取内存使用情况
 */
export function getMemoryUsage(): MemoryInfo | null {
  const perf = performance as any;
  if (perf.memory) {
    return {
      usedJSHeapSize: perf.memory.usedJSHeapSize,
      totalJSHeapSize: perf.memory.totalJSHeapSize,
      jsHeapSizeLimit: perf.memory.jsHeapSizeLimit,
    };
  }
  return null;
}

/**
 * 格式化字节数
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

/**
 * 内存监控器
 */
export class MemoryMonitor {
  private interval: NodeJS.Timeout | null = null;
  private samples: number[] = [];
  private maxSamples = 60; // 保留最近 60 个样本

  start(intervalMs = 1000): void {
    if (this.interval) return;

    this.interval = setInterval(() => {
      const memory = getMemoryUsage();
      if (memory) {
        this.samples.push(memory.usedJSHeapSize);
        if (this.samples.length > this.maxSamples) {
          this.samples.shift();
        }
      }
    }, intervalMs);
  }

  stop(): void {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  getStats(): {
    current: string;
    average: string;
    peak: string;
    trend: 'stable' | 'increasing' | 'decreasing';
  } | null {
    if (this.samples.length === 0) return null;

    const current = this.samples[this.samples.length - 1];
    const average = this.samples.reduce((a, b) => a + b, 0) / this.samples.length;
    const peak = Math.max(...this.samples);

    // 计算趋势
    let trend: 'stable' | 'increasing' | 'decreasing' = 'stable';
    if (this.samples.length > 10) {
      const recent = this.samples.slice(-10);
      const older = this.samples.slice(-20, -10);
      const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length;
      const olderAvg = older.reduce((a, b) => a + b, 0) / older.length;
      
      const diff = recentAvg - olderAvg;
      const threshold = olderAvg * 0.1; // 10% 变化
      
      if (diff > threshold) trend = 'increasing';
      else if (diff < -threshold) trend = 'decreasing';
    }

    return {
      current: formatBytes(current),
      average: formatBytes(average),
      peak: formatBytes(peak),
      trend,
    };
  }

  reset(): void {
    this.samples = [];
  }
}

/**
 * 检测内存泄漏
 */
export function detectMemoryLeak(
  threshold = 50 * 1024 * 1024 // 50MB
): boolean {
  const memory = getMemoryUsage();
  if (!memory) return false;

  // 简单检测：如果内存增长超过阈值
  return memory.usedJSHeapSize > threshold;
}

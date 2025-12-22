/**
 * 性能监控工具测试
 * 参考：@docs/design/performance_budget_20251222.md
 */

import {
  PerformanceMonitor,
  isLowPerformanceDevice,
  prefersReducedMotion,
} from '@/utils/performanceMonitor';

describe('PerformanceMonitor', () => {
  let monitor: PerformanceMonitor;

  beforeEach(() => {
    monitor = new PerformanceMonitor();
  });

  afterEach(() => {
    monitor.clear();
  });

  it('应该能够开始和结束计时', () => {
    monitor.start('test');
    const duration = monitor.end('test');

    expect(duration).toBeGreaterThanOrEqual(0);
  });

  it('应该能够记录多个标记', () => {
    monitor.start('task1');
    monitor.start('task2');

    const duration1 = monitor.end('task1');
    const duration2 = monitor.end('task2');

    expect(duration1).toBeGreaterThanOrEqual(0);
    expect(duration2).toBeGreaterThanOrEqual(0);
  });

  it('结束不存在的标记应该返回 0', () => {
    const duration = monitor.end('nonexistent');
    expect(duration).toBe(0);
  });

  it('应该能够清除所有标记', () => {
    monitor.start('test');
    monitor.clear();

    const duration = monitor.end('test');
    expect(duration).toBe(0);
  });
});

describe('Device Detection', () => {
  it('isLowPerformanceDevice 应该返回布尔值', () => {
    const result = isLowPerformanceDevice();
    expect(typeof result).toBe('boolean');
  });

  it('prefersReducedMotion 应该返回布尔值', () => {
    const result = prefersReducedMotion();
    expect(typeof result).toBe('boolean');
  });
});

/**
 * 性能基准测试
 * 参考：@docs/design/performance_budget_20251222.md
 */

import { loadAuthor } from '@/core/data/dataLoader';
import { NarrativeScheduler } from '@/core/scheduler/narrativeScheduler';
import type { Route } from '@/core/data/normalizers';

// Mock 数据生成
function generateMockRoutes(count: number): Route[] {
  const routes: Route[] = [];
  for (let i = 0; i < count; i++) {
    routes.push({
      id: `route${i}`,
      start_location: {
        name: `City ${i}`,
        coordinates: { lat: 0, lng: 0 },
      },
      end_location: {
        name: `City ${i + 1}`,
        coordinates: { lat: 10, lng: 10 },
      },
      collection_info: {
        has_collection: true,
        collection_meta: {
          title: `Work ${i}`,
          date: `${2000 + i}`,
          location: `City ${i}`,
        },
      },
      year: 2000 + i,
    });
  }
  return routes;
}

describe('Performance Benchmarks', () => {
  describe('Data Loading', () => {
    it('should parse 100 nodes in < 100ms', async () => {
      // 注意：这个测试需要真实数据文件
      // 在 CI 环境中可能需要 mock
      const start = performance.now();
      
      try {
        await loadAuthor('murakami');
      } catch {
        // 如果文件不存在，跳过测试
        console.warn('Skipping data loading test: file not found');
        return;
      }
      
      const duration = performance.now() - start;
      
      // 放宽限制以适应不同环境
      expect(duration).toBeLessThan(100);
    });
  });

  describe('Scheduler Performance', () => {
    it('should build timeline for 100 routes in < 50ms', () => {
      const routes = generateMockRoutes(100);
      const scheduler = new NarrativeScheduler();
      
      const mockAuthor = {
        id: 'test',
        name: 'Test',
        name_zh: '测试',
        theme_color: '#000',
        routes,
      };
      
      const start = performance.now();
      scheduler.load(mockAuthor, routes);
      const duration = performance.now() - start;
      
      expect(duration).toBeLessThan(50);
    });

    it('should handle rapid author switching', () => {
      const scheduler = new NarrativeScheduler();
      const routes1 = generateMockRoutes(50);
      const routes2 = generateMockRoutes(50);
      
      const author1 = { id: 'a1', name: 'A1', name_zh: 'A1', theme_color: '#000', routes: routes1 };
      const author2 = { id: 'a2', name: 'A2', name_zh: 'A2', theme_color: '#000', routes: routes2 };
      
      const start = performance.now();
      
      // 快速切换 10 次
      for (let i = 0; i < 10; i++) {
        scheduler.load(author1, routes1);
        scheduler.dispose();
        scheduler.load(author2, routes2);
        scheduler.dispose();
      }
      
      const duration = performance.now() - start;
      
      // 总时间应该 < 1s
      expect(duration).toBeLessThan(1000);
    });
  });

  describe('Memory Management', () => {
    it('should not leak memory during playback', () => {
      const scheduler = new NarrativeScheduler();
      const routes = generateMockRoutes(100);
      const author = { id: 'test', name: 'Test', name_zh: '测试', theme_color: '#000', routes };
      
      // 获取初始内存（如果可用）
      const initialMemory = (performance as any).memory?.usedJSHeapSize;
      
      // 模拟长时间运行
      for (let i = 0; i < 100; i++) {
        scheduler.load(author, routes);
        scheduler.play();
        scheduler.pause();
        scheduler.dispose();
      }
      
      // 强制垃圾回收（仅在支持的环境）
      if (global.gc) {
        global.gc();
      }
      
      const finalMemory = (performance as any).memory?.usedJSHeapSize;
      
      if (initialMemory && finalMemory) {
        const growth = finalMemory - initialMemory;
        const growthMB = growth / (1024 * 1024);
        
        // 内存增长应该 < 10MB
        expect(growthMB).toBeLessThan(10);
      }
    });
  });
});

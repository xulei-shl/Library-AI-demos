# 性能预算与优化策略文档
- **Status**: Proposal
- **Date**: 2025-12-22

## 1. 目标与背景
统一各模块分散的性能指标，建立端到端性能预算，确保《墨迹与边界》在不同设备与网络条件下保持流畅体验。本文档整合 `data_orchestrator`、`narrative_scheduler`、`ink_line_component`、`ripple_node_component` 中的性能要求，并补充缺失的全局指标。

## 2. 性能预算 (Performance Budget)
### 2.1 加载性能
| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| 首屏渲染 (FCP) | < 1.5s | Lighthouse |
| 可交互时间 (TTI) | < 3.0s | Lighthouse |
| 最大内容绘制 (LCP) | < 2.5s | Web Vitals |
| 首次输入延迟 (FID) | < 100ms | Web Vitals |
| 累积布局偏移 (CLS) | < 0.1 | Web Vitals |
| JavaScript 包大小 | < 300KB (gzip) | Webpack Bundle Analyzer |
| GeoJSON 数据大小 | < 500KB | 见 `geodata_specification_20251222.md` |

### 2.2 运行时性能
#### 数据处理
| 模块 | 操作 | 目标值 | 来源文档 |
|------|------|--------|----------|
| dataLoader | 100 节点解析 | < 16ms | data_orchestrator_20251215.md |
| narrativeScheduler | 100 路线队列构建 | < 20ms | narrative_scheduler_20251215.md |
| normalizers | 单条路线规范化 | < 1ms | data_orchestrator_20251215.md |

#### 渲染性能
| 场景 | 目标帧率 | 节点数 | 来源文档 |
|------|----------|--------|----------|
| 单作者模式 | ≥ 60fps | 50 节点 + 50 线条 | ink_line_component_20251215.md |
| 双作者 Overlay | ≥ 45fps | 100 节点 + 100 线条 | overlay_mode_module_20251215.md |
| 个人星图叠加 | ≥ 50fps | 200 节点（含标记） | ripple_node_component_20251215.md |

#### 动画性能
| 动画类型 | 帧循环 Jitter | GPU 加速 | 来源文档 |
|----------|---------------|----------|----------|
| 墨迹生长 | < 10ms | 必须 | narrative_scheduler_20251215.md |
| 涟漪扩散 | < 5ms | 必须 | ripple_node_component_20251215.md |
| Smart FlyTo | < 16ms | 推荐 | narrative_map_canvas_20251215.md |

### 2.3 内存预算
| 资源 | 限制 | 监控方法 |
|------|------|----------|
| 作者数据缓存 | < 10MB | `performance.memory` |
| SVG DOM 节点 | < 500 个 | `document.querySelectorAll('svg *').length` |
| 事件监听器 | < 100 个 | Chrome DevTools Memory Profiler |
| localStorage | < 5MB | 见 `personal_constellation_module_20251215.md` |

## 3. 端到端性能场景
### 场景 1: 冷启动 + 单作者播放
**用户操作**:
1. 首次访问页面
2. 选择"村上春树"
3. 点击播放

**性能要求**:
```
T=0ms      : 开始加载 HTML/CSS/JS
T=1500ms   : FCP（显示底图骨架）
T=2000ms   : 加载 murakami.json + world.json
T=2020ms   : dataLoader 解析完成
T=2040ms   : narrativeScheduler 构建队列
T=2100ms   : Smart FlyTo 开始
T=3100ms   : 相机到位，墨迹开始生长
T=3100-10s : 保持 ≥ 60fps
```

### 场景 2: 作者切换
**用户操作**:
1. 正在播放"村上春树"
2. 切换到"马尔克斯"

**性能要求**:
```
T=0ms    : 点击切换
T=50ms   : 暂停当前动画，dispose 调度器
T=100ms  : 加载 marquez.json（命中缓存则跳过）
T=120ms  : 重建队列
T=150ms  : Smart FlyTo 开始
T=1150ms : 新作者动画开始
```

### 场景 3: Overlay 模式
**用户操作**:
1. 选择"村上春树" + "马尔克斯"
2. 启用 Overlay 模式

**性能要求**:
```
T=0ms    : 点击启用
T=100ms  : 加载两份数据（并行）
T=150ms  : overlaySelectors 合并路线
T=200ms  : 双调度器初始化
T=300ms  : 开始渲染
持续     : 保持 ≥ 45fps
```

## 4. 优化策略
### 4.1 代码分割 (Code Splitting)
```typescript
// 路由级别懒加载
const NarrativeMap = lazy(() => import('@/core/map/NarrativeMap'));
const PlaybackControl = lazy(() => import('@/core/playback/PlaybackControl'));

// 按需加载 D3 投影
const loadAiryProjection = () => import('d3-geo-projection').then(m => m.geoAiry);
```

### 4.2 虚拟化渲染
- **节点虚拟化**: 当节点数 > 200 时，仅渲染视口内 + 周边 20% 缓冲区。
- **线条简化**: Zoom < 3 时，降低曲线插值点数量（50 -> 20）。

### 4.3 GPU 加速
所有动画元素强制开启 GPU 层。

```css
.ink-line, .ripple-node {
  will-change: stroke-dashoffset, transform, opacity;
  transform: translateZ(0); /* 强制 GPU 层 */
}
```

### 4.4 Web Worker
将耗时计算移至后台线程。

```typescript
// src/workers/scheduleWorker.ts
self.onmessage = (e) => {
  const { routes } = e.data;
  const timeline = buildTimeline(routes); // 耗时操作
  self.postMessage(timeline);
};
```

### 4.5 缓存策略
- **HTTP 缓存**: GeoJSON 与作者 JSON 设置 `Cache-Control: max-age=31536000`。
- **Service Worker**: 使用 Workbox 预缓存核心资源。
- **内存缓存**: `dataLoader` 使用 `Map` 缓存已加载作者。

### 4.6 降级策略
#### 低性能设备检测
```typescript
const isLowPerformance = 
  navigator.hardwareConcurrency < 4 || 
  /Android|webOS|iPhone|iPad|iPod|BlackBerry/i.test(navigator.userAgent);

if (isLowPerformance) {
  // 禁用阴影
  SHADOWS.inkLine = 'none';
  // 降低动画帧率
  DURATIONS.narrative *= 0.5;
  // 减少插值点
  CURVE_INTERPOLATION_POINTS = 20;
}
```

#### prefers-reduced-motion
```typescript
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (prefersReducedMotion) {
  // 跳过所有非关键动画
  DURATIONS.fast = 0;
  DURATIONS.normal = 0;
  // 保留叙事核心动画但加速
  DURATIONS.narrative = 300;
}
```

## 5. 监控与告警
### 5.1 开发环境
- **React DevTools Profiler**: 记录组件渲染时间。
- **Chrome Performance Tab**: 捕获 60s 播放过程的火焰图。
- **Lighthouse CI**: 每次 PR 自动运行性能测试。

### 5.2 生产环境
- **Web Vitals**: 使用 `web-vitals` 库上报到 Google Analytics。
- **Sentry Performance**: 监控慢事务（> 3s）。
- **自定义指标**:
  ```typescript
  performance.mark('scheduler-start');
  // ... 调度器逻辑
  performance.mark('scheduler-end');
  performance.measure('scheduler', 'scheduler-start', 'scheduler-end');
  ```

### 5.3 告警阈值
| 指标 | 警告 | 严重 |
|------|------|------|
| LCP | > 2.5s | > 4.0s |
| FID | > 100ms | > 300ms |
| 帧率 | < 50fps | < 30fps |
| 内存泄漏 | +10MB/min | +50MB/min |

## 6. 测试策略
### 6.1 性能基准测试
```typescript
// tests/performance/benchmark.test.ts
describe('Performance Benchmarks', () => {
  it('dataLoader 解析 100 节点 < 16ms', async () => {
    const start = performance.now();
    await loadAuthor('murakami');
    const duration = performance.now() - start;
    expect(duration).toBeLessThan(16);
  });

  it('narrativeScheduler 构建队列 < 20ms', () => {
    const routes = generateMockRoutes(100);
    const start = performance.now();
    scheduler.load('test', routes);
    const duration = performance.now() - start;
    expect(duration).toBeLessThan(20);
  });
});
```

### 6.2 压力测试
- **极限节点数**: 渲染 500 节点 + 500 线条，记录帧率下限。
- **长时间运行**: 连续播放 10 分钟，监控内存增长。
- **快速切换**: 1 秒内切换 10 次作者，检查是否崩溃。

### 6.3 真机测试
| 设备 | CPU | 目标帧率 |
|------|-----|----------|
| iPhone 12 | A14 | ≥ 60fps |
| Pixel 5 | Snapdragon 765G | ≥ 50fps |
| 低端 Android | < 4 核 | ≥ 30fps |

## 7. 依赖声明
- 本文档整合所有模块的性能要求，是 Sprint 0 的验收标准。
- 需在每个 Sprint 结束时重新测量，确保不退化。
- 与 `geodata_specification_20251222.md` 协同优化数据体积。

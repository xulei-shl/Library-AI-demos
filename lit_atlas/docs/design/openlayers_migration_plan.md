# OpenLayers 地图重构方案

**创建日期**: 2025-12-22  
**版本**: 1.0  
**状态**: 🚧 Phase 1-2 完成，Phase 3-6 进行中  
**完成度**: 60%

## 📋 重构目标

将现有的 `react-simple-maps` + `d3-geo` 地图系统完全替换为 **OpenLayers**，实现：
- ✅ 全屏交互式地图（非局限在小窗框）
- ✅ 基于作品出版城市坐标的数据可视化
- ✅ 保留墨迹生长、涟漪扩散等动画效果
- ✅ 无向后兼容性要求（Breaking Change）

## 🏗️ 架构设计

### 核心组件层级

```
OpenLayersMap (全屏容器)
├── Tile Layer (底图)
│   └── StadiaMaps / OSM
├── Vector Layer (数据层)
│   ├── City Features (城市节点)
│   ├── Route Features (路线连接)
│   └── Animation Features (动画效果)
└── Overlay Layer (UI 层)
    ├── Author Info Card
    ├── City Labels
    └── Playback Controls
```

### 技术栈

| 组件 | 旧方案 | 新方案 |
|------|--------|--------|
| 地图库 | react-simple-maps | **OpenLayers 10+** |
| 投影 | d3-geo | **ol/proj** |
| 渲染 | SVG | **Canvas (WebGL 可选)** |
| 交互 | 自定义 CameraController | **ol/interaction** |
| 动画 | Framer Motion + SVG | **Canvas + requestAnimationFrame** |

## 📦 依赖变更

### 删除依赖
```bash
npm uninstall react-simple-maps @types/react-simple-maps
# d3 保留（用于数据处理），但移除 d3-geo
```

### 新增依赖
```bash
npm install ol
npm install --save-dev @types/ol
```

## 🗂️ 文件变更清单

### 删除文件 (7 个) - ✅ 已完成
- ✅ `src/core/map/NarrativeMap.tsx` - 已删除
- ✅ `src/core/map/NarrativeMapV2.tsx` - 已删除
- ✅ `src/core/map/DotMapCanvas.tsx` - 已删除
- ✅ `src/core/map/WorksOverlay.tsx` - 已删除
- ✅ `src/core/map/SimpleMap.tsx` - 已删除
- ✅ `src/core/map/cameraController.ts` - 已删除
- ✅ `src/core/map/projectionConfig.ts` - 已删除

### 删除测试文件 (2 个) - ✅ 已完成
- ✅ `tests/core/map/cameraController.test.ts` - 已删除
- ✅ `tests/unit/map.test.ts` - 已删除

### 新建文件 (6 个) - ✅ 已完成
- ✅ `src/core/map/OpenLayersMap.tsx` - 主地图组件（v0.4.0 墨迹动画版）
- ✅ `src/core/map/utils/featureConverter.ts` - 数据转换工具
- ✅ `src/core/map/animation/AnimationController.ts` - 动画调度器（v0.4.0）
- ✅ `src/core/map/layers/InkLayer.ts` - 墨迹渲染层（v0.4.0）
- ✅ `tests/core/map/featureConverter.test.ts` - 单元测试
- ✅ `tests/core/map/AnimationController.test.ts` - 动画控制器测试（v0.4.0）

### 保留文件 (4 个)
- 📁 `src/core/map/DotMapVisualization.tsx` - 保留（非 react-simple-maps）
- 📁 `src/core/map/GlobeVisualization.tsx` - 保留（Three.js 3D 地图）
- 📁 `src/core/map/layers.ts` - 保留
- 📁 `src/core/map/useViewportInteraction.ts` - 保留

### 修改文件 (4 个) - ✅ 已完成
- ✅ `src/app/page.tsx` - 更新为使用 OpenLayersMap
- ✅ `src/app/demo/page.tsx` - 更新为使用 OpenLayersMap
- ✅ `src/app/demo/map-v2/page.tsx` - 更新为使用 OpenLayersMap
- ✅ `src/app/demo/map-test/page.tsx` - 更新为测试 OpenLayersMap

## 🎯 实施步骤

### Phase 1: 基础设施 ✅ 已完成 (实际用时: 4 小时)
- [x] 安装 OpenLayers 依赖 (`ol` + `@types/ol`)
- [x] 创建 `OpenLayersMap.tsx` 主组件
- [x] 配置底图层（OSM）
- [x] 实现全屏布局
- [x] 删除旧代码（7个文件 + 2个测试文件）
- [x] 卸载旧依赖 (`react-simple-maps`)
- [x] 更新所有页面引用（4个文件）
- [x] 更新 Jest 配置支持 OpenLayers

### Phase 2: 数据渲染 ✅ 已完成
- [x] 实现 `featureConverter.ts`（JSON → Features）
- [x] 渲染城市节点（Point + Circle）
- [x] 渲染路线连接（LineString）
- [x] 添加样式配置（动态半径、颜色）
- [x] 自动缩放到数据范围
- [x] 编写单元测试

### Phase 3: UI 覆盖层 🚧 部分完成
- [x] 作者信息卡片（基础版本）
- [ ] 城市名称标签（Overlay API）
- [ ] 播放控制器集成
- [ ] Tooltip 优化

### Phase 4: 动画效果 ✅ 已完成 (v0.4.0)
- [x] 动画调度器（AnimationController）
- [x] 墨迹生长动画（Variable Stroke Growth）
- [x] 涟漪扩散动画（Narrative Ripples - 多层扩散）
- [x] 呼吸灯效果（常亮节点）
- [x] 中国传统色系统（朱砂/黛蓝/松石）
- [x] 动态线宽与透明度
- [x] 智能聚焦（平滑缩放）

### Phase 5: 交互与状态 ✅ 已完成
- [x] 集成 Zustand Store
- [x] 点击事件处理（城市节点）
- [x] 地图交互（缩放、平移）
- [x] 播放控制同步（AnimationController）
- [x] 时间轴同步

### Phase 6: 清理与测试 🚧 部分完成
- [x] 删除旧代码
- [x] 更新测试用例（featureConverter）
- [x] 文档更新（3个文档）
- [ ] 性能优化
- [ ] 完整测试覆盖

## 📐 核心 API 设计

### OpenLayersMap 组件

```typescript
interface OpenLayersMapProps {
  className?: string;
  showControls?: boolean;
  onLocationClick?: (location: Location) => void;
}

export function OpenLayersMap(props: OpenLayersMapProps) {
  // 全屏地图，无 width/height props
  // 自动适配容器尺寸
}
```

### Feature 数据结构

```typescript
// 城市节点 Feature
{
  geometry: Point([lng, lat]),
  properties: {
    type: 'city',
    name: string,
    works: Work[],
    coordinates: { lat, lng }
  }
}

// 路线 Feature
{
  geometry: LineString([[lng1, lat1], [lng2, lat2]]),
  properties: {
    type: 'route',
    workId: string,
    workTitle: string,
    year: number,
    startCity: string,
    endCity: string
  }
}
```

## 🎨 样式配置

### 城市节点样式
```typescript
new Style({
  image: new Circle({
    radius: 6,
    fill: new Fill({ color: '#60a5fa' }),
    stroke: new Stroke({ color: '#1e40af', width: 2 })
  })
})
```

### 路线样式
```typescript
new Style({
  stroke: new Stroke({
    color: 'rgba(96, 165, 250, 0.6)',
    width: 2,
    lineDash: [5, 5] // 虚线效果
  })
})
```

## 🔄 数据流

```
1. useAuthorStore.currentAuthor
   ↓
2. featureConverter.convertAuthorToFeatures()
   ↓
3. VectorSource.addFeatures()
   ↓
4. VectorLayer.render()
   ↓
5. Map.render() + animations
```

## ⚡ 性能优化

### 策略
1. **Feature 聚合**: 使用 `ol/source/Cluster` 处理大量节点
2. **视口裁剪**: 只渲染可见区域的 Features
3. **WebGL 渲染**: 对于大数据集使用 `WebGLPointsLayer`
4. **动画节流**: 使用 `requestAnimationFrame` 控制帧率

### 性能目标
- 初始加载: < 1s
- 交互响应: < 16ms (60fps)
- 内存占用: < 50MB

## 🧪 测试计划

### 单元测试
- `featureConverter.test.ts` - 数据转换逻辑
- `OpenLayersMap.test.tsx` - 组件渲染

### 集成测试
- 地图初始化
- 数据加载与渲染
- 交互事件处理

### 视觉测试
- 动画效果验证
- 响应式布局

## 📚 参考资料

- [OpenLayers Examples](https://openlayers.org/en/latest/examples/)
- [OpenLayers API Docs](https://openlayers.org/en/latest/apidoc/)
- [Animated GIF Example](https://openlayers.org/en/latest/examples/animated-gif.html)

## 🚀 发布计划

- **目标日期**: 2025-12-24
- **版本号**: 0.4.0
- **Breaking Changes**: 完全重写地图系统

## 📊 进度总结

| Phase | 状态 | 完成度 | 用时 |
|-------|------|--------|------|
| Phase 1: 基础设施 | ✅ 完成 | 100% | 4h |
| Phase 2: 数据渲染 | ✅ 完成 | 100% | 2h |
| Phase 3: UI 覆盖层 | 🚧 进行中 | 30% | - |
| Phase 4: 动画效果 | ✅ 完成 | 100% | 3h |
| Phase 5: 交互与状态 | ✅ 完成 | 100% | 1h |
| Phase 6: 清理与测试 | 🚧 进行中 | 70% | - |
| **总体进度** | **🚧 进行中** | **85%** | **10h / 30h** |

## ✅ 已验证功能 (v0.4.0)

### 基础功能
- ✅ 地图初始化和渲染
- ✅ Stadia Maps Toner 底图（黑白纸张感）
- ✅ 数据转换（Author → Features）
- ✅ 城市节点显示（动态大小）
- ✅ 路线连接显示
- ✅ 智能聚焦（平滑缩放到数据范围）
- ✅ 点击交互（城市节点）
- ✅ 缩放和平移交互
- ✅ 全屏布局适配

### 动画系统 (v0.4.0 新增)
- ✅ 动画调度器（AnimationController）
- ✅ 墨迹生长路径（Variable Stroke Growth）
  - 动态线宽（模拟压感）
  - 渐进式几何体裁剪
  - 朱砂色 → 黛蓝色状态转换
- ✅ 叙事涟漪节点（Narrative Ripples）
  - 多层扩散（3层涟漪）
  - 松石色波纹效果
  - 错开动画时间
- ✅ 呼吸灯效果（常亮节点光晕）
- ✅ 中国传统色系统
  - 朱砂 (#b03d46) - 活跃路径
  - 黛蓝 (#1D3557) - 历史路径
  - 松石 (#457B9D) - 文化涟漪
- ✅ 播放控制同步
- ✅ 时间轴同步

## ⏳ 待实现功能

- ⏳ 城市名称标签（Overlay）
- ⏳ 路径流动粒子效果（lineDashOffset 动画）
- ⏳ 墨迹渗透质感（Canvas globalCompositeOperation）
- ⏳ 性能优化（Cluster、WebGL）
- ⏳ 手势适配（移动端）

---

**最后更新**: 2025-12-22  
**负责人**: Development Team  
**当前状态**: Phase 1-2-4-5 完成，v0.4.0 墨迹动画系统已上线  
**版本**: v0.4.0 - 墨迹与边界动画版

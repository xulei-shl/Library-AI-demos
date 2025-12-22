# 开发变更记录 - OpenLayers 地图重构

**日期**: 2025-12-22  
**对应设计文档**: [docs/design/openlayers_migration_plan.md](../design/openlayers_migration_plan.md)  
**变更类型**: 🔥 Breaking Change - 完全重构

## 1. 变更摘要

将项目的地图系统从 `react-simple-maps` + `d3-geo` 完全迁移到 **OpenLayers**，实现全屏交互式地图体验。

### 核心改进
- ✅ 全屏地图布局（非局限在小窗框）
- ✅ 原生交互支持（缩放、平移、点击）
- ✅ 基于作品出版城市坐标的数据可视化
- ✅ 更好的性能和扩展性
- ✅ 无向后兼容性负担

## 2. 文件清单

### 新增文件 (3个)
- `src/core/map/OpenLayersMap.tsx` - 主地图组件（全屏）
- `src/core/map/utils/featureConverter.ts` - 数据转换工具（JSON → OpenLayers Features）
- `docs/design/openlayers_migration_plan.md` - 迁移方案设计文档

### 删除文件 (7个)
- ❌ `src/core/map/NarrativeMap.tsx` - 旧的 react-simple-maps 地图
- ❌ `src/core/map/NarrativeMapV2.tsx` - 旧的点阵地图
- ❌ `src/core/map/DotMapCanvas.tsx` - 旧的 Canvas 地图
- ❌ `src/core/map/WorksOverlay.tsx` - 旧的作品覆盖层
- ❌ `src/core/map/SimpleMap.tsx` - 旧的简单地图
- ❌ `src/core/map/cameraController.ts` - 旧的相机控制器
- ❌ `src/core/map/projectionConfig.ts` - 旧的投影配置

### 删除测试文件 (2个)
- ❌ `tests/core/map/cameraController.test.ts`
- ❌ `tests/unit/map.test.ts`

### 修改文件 (4个)
- 🔧 `src/app/page.tsx` - 更新为使用 OpenLayersMap
- 🔧 `src/app/demo/page.tsx` - 更新为使用 OpenLayersMap
- 🔧 `src/app/demo/map-v2/page.tsx` - 更新为使用 OpenLayersMap
- 🔧 `src/app/demo/map-test/page.tsx` - 更新为测试 OpenLayersMap

### 依赖变更
```bash
# 新增
+ ol@^10.x
+ @types/ol@^10.x

# 删除
- react-simple-maps@^3.0.0
- @types/react-simple-maps@^3.0.6
```

## 3. 技术实现细节

### 3.1 数据转换流程

```typescript
// 旧方案：直接在组件中使用 d3-geo 投影
const projection = d3.geoNaturalEarth1()
  .scale(width / 6)
  .translate([width / 2, height / 2]);

// 新方案：使用 OpenLayers 的 Feature 系统
const features = convertAuthorToFeatures(author);
vectorSource.addFeatures(features);
```

### 3.2 Feature 数据结构

```typescript
// 城市节点 Feature
{
  geometry: Point(fromLonLat([lng, lat])),
  properties: {
    type: 'city',
    name: string,
    coordinates: { lat, lng },
    works: Work[],
    routeCount: number
  }
}

// 路线 Feature
{
  geometry: LineString([
    fromLonLat([lng1, lat1]),
    fromLonLat([lng2, lat2])
  ]),
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

### 3.3 样式系统

```typescript
// 城市节点：根据路线数量动态调整大小
const radius = Math.min(6 + routeCount * 2, 16);
new Style({
  image: new Circle({
    radius,
    fill: new Fill({ color: '#60a5fa' }),
    stroke: new Stroke({ color: '#1e40af', width: 2 })
  })
});

// 路线：半透明蓝色线条
new Style({
  stroke: new Stroke({
    color: 'rgba(96, 165, 250, 0.4)',
    width: 2
  })
});
```

### 3.4 交互实现

```typescript
// 地图点击事件
map.on('click', (event) => {
  const features = map.getFeaturesAtPixel(event.pixel);
  if (features && isCityFeature(features[0])) {
    onLocationClick({
      type: 'city',
      name: features[0].get('name'),
      coordinates: features[0].get('coordinates')
    });
  }
});

// 自动缩放到数据范围
const extent = vectorSource.getExtent();
map.getView().fit(extent, {
  padding: [50, 50, 50, 50],
  duration: 1000,
  maxZoom: 6
});
```

## 4. 测试结果

### 编译检查
```bash
npm run typecheck
```

**状态**: ⚠️ 部分通过
- ✅ 地图相关代码：无类型错误
- ⚠️ 其他模块：11个错误（与地图重构无关，为旧代码遗留问题）

### 待修复的非地图错误
1. `SpeedMenu.tsx` - EASING.standard 不存在（4处）
2. `timelineBuilder.ts` - collectionMeta 类型不匹配（1处）
3. `performanceOptimizer.ts` - window.setTimeout 类型问题（1处）
4. 测试文件 - mockAuthor 类型不匹配（5处）

### 功能验证
- [ ] 地图初始化
- [ ] 数据加载与渲染
- [ ] 城市节点显示
- [ ] 路线连接显示
- [ ] 点击交互
- [ ] 自动缩放

**注意**: 需要真实数据文件才能完整测试

## 5. 后续任务

### Phase 2: 动画效果（待实现）
- [ ] 墨迹生长动画（Canvas + postrender）
- [ ] 涟漪扩散动画
- [ ] 路线流动效果
- [ ] 节点闪烁效果

### Phase 3: UI 覆盖层（待实现）
- [ ] 城市名称标签（Overlay API）
- [ ] 作者信息卡片优化
- [ ] 播放控制器集成

### Phase 4: 性能优化（待实现）
- [ ] Feature 聚合（Cluster）
- [ ] 视口裁剪
- [ ] WebGL 渲染（可选）

## 6. 破坏性变更说明

### API 变更
```typescript
// 旧 API
<NarrativeMapV2
  width={1200}
  height={800}
  showControls={true}
/>

// 新 API（全屏，无需 width/height）
<OpenLayersMap
  showControls={true}
/>
```

### 布局变更
- 旧方案：地图局限在固定尺寸的容器中
- 新方案：地图自动填充父容器，支持全屏

### 依赖变更
- 移除 `react-simple-maps` 和 `d3-geo`
- 新增 `ol` (OpenLayers)

## 7. 运行指南

### 安装依赖
```bash
npm install --legacy-peer-deps
```

### 启动开发服务器
```bash
npm run dev
```

### 访问测试页面
- 主页面: http://localhost:3000
- 地图测试: http://localhost:3000/demo/map-test
- 演示页面: http://localhost:3000/demo

## 8. 已知问题

1. **类型错误**: 11个非地图相关的类型错误需要修复
2. **动画缺失**: 墨迹生长和涟漪动画尚未实现
3. **测试缺失**: 需要为新地图组件编写测试用例
4. **数据加载**: 需要真实的作者数据文件进行完整测试

## 9. 参考资料

- [OpenLayers 官方文档](https://openlayers.org/en/latest/apidoc/)
- [OpenLayers Examples](https://openlayers.org/en/latest/examples/)
- [Animated GIF Example](https://openlayers.org/en/latest/examples/animated-gif.html)
- [迁移方案设计文档](../design/openlayers_migration_plan.md)

---

**变更完成时间**: 2025-12-22  
**开发者**: Development Team  
**审查状态**: ⏳ 待审查

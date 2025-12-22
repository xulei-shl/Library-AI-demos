# 地理数据规范文档
- **Status**: Proposal
- **Date**: 2025-12-22

## 1. 目标与背景
定义《墨迹与边界》使用的 GeoJSON 底图数据来源、格式、简化策略与投影参数，确保 `NarrativeMap` 与 `InkLine` 组件能正确渲染地理要素。本文档解决设计文档中"GeoJSON 底图"未明确定义的问题。

## 2. 详细设计
### 2.1 数据来源与许可
- **来源**: [Natural Earth](https://www.naturalearthdata.com/) 1:50m Cultural Vectors
- **许可**: Public Domain（无需署名）
- **下载地址**: `https://www.naturalearthdata.com/downloads/50m-cultural-vectors/`
- **使用图层**:
  - `ne_50m_admin_0_countries.geojson` (国家边界)
  - `ne_50m_coastline.geojson` (海岸线，可选)

### 2.2 数据处理流程
#### 简化策略
原始 GeoJSON 文件过大（~23MB），需简化以提升性能。

```bash
# 使用 mapshaper 简化（保留 0.5% 顶点）
npx mapshaper ne_50m_admin_0_countries.geojson \
  -simplify 0.5% \
  -o format=geojson public/data/geo/world-simplified.json
```

**预期结果**:
- 文件大小: ~500KB
- 顶点数: ~15,000
- 视觉质量: 在 Zoom 1-8 下无明显失真

#### 字段裁剪
仅保留必要属性以减少体积。

```javascript
// scripts/processGeoData.js
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('input.geojson'));

data.features = data.features.map(f => ({
  type: f.type,
  geometry: f.geometry,
  properties: {
    name: f.properties.NAME,      // 国家名称
    iso_a3: f.properties.ISO_A3,  // ISO 代码
  },
}));

fs.writeFileSync('public/data/geo/world.json', JSON.stringify(data));
```

### 2.3 存储路径
```
public/data/geo/
├── world.json              # 简化后的国家边界
├── cities.json             # 城市坐标（手动维护）
└── README.md               # 数据来源说明
```

### 2.4 城市坐标数据
作者路线中的城市需要预定义坐标。

**`public/data/geo/cities.json`**:
```json
{
  "Shanghai": {
    "coordinates": [121.4737, 31.2304],
    "name_zh": "上海",
    "country": "CHN"
  },
  "Tokyo": {
    "coordinates": [139.6917, 35.6895],
    "name_zh": "东京",
    "country": "JPN"
  },
  "New York": {
    "coordinates": [-74.0060, 40.7128],
    "name_zh": "纽约",
    "country": "USA"
  }
}
```

**维护策略**:
- 初期手动添加高频城市（~50 个）
- 后期可接入 GeoNames API 自动补全

### 2.5 投影配置
基于需求文档 `@docs/墨迹与边界-0.3.md` 的建议。

#### 推荐投影: Natural Earth I
```typescript
// src/core/map/projectionConfig.ts
import { geoNaturalEarth1 } from 'd3-geo';

export const DEFAULT_PROJECTION = geoNaturalEarth1()
  .center([0, 0])           // 中心点（本初子午线）
  .rotate([0, 0, 0])        // 旋转角度
  .scale(160)               // 缩放比例
  .translate([width / 2, height / 2]); // 画布中心
```

**特性**:
- 伪圆柱投影，视觉平衡
- 适合全球视图
- D3 原生支持，无需额外库

#### 备选投影: Airy (实验性)
```typescript
import { geoAiry } from 'd3-geo-projection';

export const AIRY_PROJECTION = geoAiry()
  .radius(90)  // 视角半径
  .scale(100);
```

**注意**: `d3-geo-projection` 需单独安装。

### 2.6 曲线算法
修正 `ink_line_component_20251215.md` 中的错误。

**正确 API**:
```typescript
import { geoPath, geoInterpolate } from 'd3-geo';

// 生成大圆航线（Great Circle）
const interpolate = geoInterpolate(fromCoords, toCoords);
const points = Array.from({ length: 50 }, (_, i) => 
  interpolate(i / 49)
);

// 转换为 SVG 路径
const pathGenerator = geoPath().projection(projection);
const pathData = pathGenerator({
  type: 'LineString',
  coordinates: points,
});
```

**不存在的 API**:
- ❌ `d3.geoCurve` (文档错误)
- ✅ 使用 `geoInterpolate` + `geoPath`

### 2.7 性能优化
#### 虚拟化渲染
当 Zoom < 3 时，仅渲染大陆轮廓，隐藏小岛屿。

```typescript
const filteredFeatures = features.filter(f => {
  const area = geoArea(f); // 计算面积
  return area > MIN_AREA_THRESHOLD;
});
```

#### 预计算路径
在数据加载时预计算所有 SVG `d` 属性，避免运行时重复计算。

```typescript
// src/core/data/dataLoader.ts
const precomputedPaths = routes.map(route => ({
  ...route,
  svgPath: generateCurvePath(route.from, route.to),
}));
```

## 3. 测试策略
1. **数据完整性**: 校验 GeoJSON 符合 RFC 7946 规范。
2. **坐标有效性**: 所有城市坐标在 [-180, 180] × [-90, 90] 范围内。
3. **投影精度**: 对比 Natural Earth 与 Airy 投影的视觉差异，记录截图。
4. **性能基准**: 加载 `world.json` 并渲染到 Canvas，测量时间 < 100ms。
5. **曲线平滑度**: 生成 Tokyo -> New York 路径，断言至少包含 30 个插值点。

## 4. 依赖声明
- 本文档是 `narrative_map_canvas_20251215.md` 与 `ink_line_component_20251215.md` 的前置依赖。
- 需在 Sprint 0 完成数据准备，Sprint 1 开始前验证投影配置。
- 依赖包: `d3-geo@^3.1.0`, `d3-geo-projection@^4.0.0` (可选)

## 5. 附录：数据处理脚本
**`scripts/processGeoData.js`**:
```javascript
#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const INPUT = 'raw/ne_50m_admin_0_countries.geojson';
const OUTPUT = 'public/data/geo/world.json';

console.log('Processing GeoJSON...');
const data = JSON.parse(fs.readFileSync(INPUT, 'utf8'));

// 裁剪字段
data.features = data.features.map(f => ({
  type: f.type,
  geometry: f.geometry,
  properties: {
    name: f.properties.NAME,
    iso: f.properties.ISO_A3,
  },
}));

// 写入输出
fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });
fs.writeFileSync(OUTPUT, JSON.stringify(data));

console.log(`✓ Saved to ${OUTPUT}`);
console.log(`  Features: ${data.features.length}`);
console.log(`  Size: ${(fs.statSync(OUTPUT).size / 1024).toFixed(2)} KB`);
```

**运行**:
```bash
node scripts/processGeoData.js
```

# 地理数据说明

## 数据来源

### 国家边界数据
- **来源**: [Natural Earth](https://www.naturalearthdata.com/)
- **版本**: 1:50m Cultural Vectors
- **许可**: Public Domain（无需署名）
- **文件**: `world.json`（简化版）

### 城市坐标数据
- **来源**: 手动维护
- **文件**: `cities.json`
- **包含**: 50 个主要城市的坐标和中文名称

## 数据处理

原始 GeoJSON 文件经过以下处理：
1. 使用 mapshaper 简化几何形状（保留 0.5% 顶点）
2. 裁剪不必要的属性字段
3. 压缩文件大小以提升加载性能

## 使用方法

```typescript
// 加载国家边界
import worldData from '@/public/data/geo/world.json';

// 加载城市坐标
import citiesData from '@/public/data/geo/cities.json';

// 获取城市坐标
const shanghai = citiesData['Shanghai'];
console.log(shanghai.coordinates); // [121.4737, 31.2304]
```

## 数据更新

如需添加新城市或更新坐标，请编辑 `cities.json` 文件。

如需更新国家边界数据，请运行：
```bash
node scripts/processGeoData.js
```

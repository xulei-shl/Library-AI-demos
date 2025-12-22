/**
 * 曲线生成工厂
 * 使用D3生成地理曲线路径
 * 参考：@docs/design/ink_line_component_20251215.md
 */

import { geoPath, geoNaturalEarth1 } from 'd3-geo';
import { geoInterpolate } from 'd3-geo';

/**
 * 创建曲线路径
 * @param coordinates 坐标数组 [[lng, lat], ...]
 * @returns SVG路径字符串
 */
export function createCurvePath(coordinates: [number, number][]): string {
  if (coordinates.length < 2) {
    return '';
  }

  // 使用Natural Earth投影
  const projection = geoNaturalEarth1();
  const pathGenerator = geoPath().projection(projection);

  // 如果只有两个点，生成大圆弧线
  if (coordinates.length === 2) {
    return createGreatCirclePath(coordinates[0], coordinates[1], projection);
  }

  // 多个点，生成LineString
  const lineString = {
    type: 'LineString' as const,
    coordinates,
  };

  const path = pathGenerator(lineString);
  return path || '';
}

/**
 * 创建大圆弧线路径
 * @param start 起点 [lng, lat]
 * @param end 终点 [lng, lat]
 * @param projection 投影函数
 * @returns SVG路径字符串
 */
function createGreatCirclePath(
  start: [number, number],
  end: [number, number],
  projection: any
): string {
  // 使用D3的地理插值生成大圆弧
  const interpolate = geoInterpolate(start, end);
  
  // 生成中间点（根据距离决定点数）
  const distance = calculateDistance(start, end);
  const numPoints = Math.max(10, Math.min(50, Math.floor(distance / 100)));
  
  const points: [number, number][] = [];
  for (let i = 0; i <= numPoints; i++) {
    const t = i / numPoints;
    const point = interpolate(t);
    points.push(point as [number, number]);
  }

  // 投影到屏幕坐标
  const projectedPoints = points
    .map(point => projection(point))
    .filter(point => point !== null);

  if (projectedPoints.length < 2) {
    return '';
  }

  // 生成SVG路径
  let path = `M ${projectedPoints[0][0]},${projectedPoints[0][1]}`;
  
  for (let i = 1; i < projectedPoints.length; i++) {
    path += ` L ${projectedPoints[i][0]},${projectedPoints[i][1]}`;
  }

  return path;
}

/**
 * 计算两点之间的大圆距离（公里）
 */
function calculateDistance(
  start: [number, number],
  end: [number, number]
): number {
  const R = 6371; // 地球半径（公里）
  
  const lat1 = (start[1] * Math.PI) / 180;
  const lat2 = (end[1] * Math.PI) / 180;
  const deltaLat = ((end[1] - start[1]) * Math.PI) / 180;
  const deltaLon = ((end[0] - start[0]) * Math.PI) / 180;

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  
  return R * c;
}

/**
 * 简化路径（减少点数以提高性能）
 * @param path SVG路径字符串
 * @param tolerance 容差值
 * @returns 简化后的路径
 */
export function simplifyPath(path: string, tolerance: number = 1): string {
  // 这里可以实现Douglas-Peucker算法或使用simplify-js库
  // 暂时返回原路径
  return path;
}

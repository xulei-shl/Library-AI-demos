import * as d3 from 'd3';
import { Coordinate, Location } from '../../core/data/normalizers';

/**
 * 地理坐标工具模块
 * 统一地理投影、边界盒计算与误差校验逻辑
 */

// 地理投影配置
export const DEFAULT_PROJECTION = d3.geoMercator();
export const PROJECTION_CONFIG = {
  // 中国为中心的投影配置
  center: [105, 35], // 经度、纬度
  scale: 800,
  translate: [400, 300] // SVG中心点
};

/**
 * 地理边界盒类型
 */
export interface BoundingBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

/**
 * 投影点类型
 */
export interface ProjectedPoint {
  x: number;
  y: number;
}

/**
 * 计算两点间的地理距离（公里）
 * 使用Haversine公式
 * @param coord1 第一个坐标点
 * @param coord2 第二个坐标点
 * @returns 距离（公里）
 */
export function calculateDistance(coord1: Coordinate, coord2: Coordinate): number {
  const R = 6371; // 地球半径（公里）
  const dLat = toRadians(coord2.lat - coord1.lat);
  const dLng = toRadians(coord2.lng - coord1.lng);
  
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadians(coord1.lat)) * Math.cos(toRadians(coord2.lat)) *
    Math.sin(dLng / 2) * Math.sin(dLng / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * 角度转弧度
 * @param degrees 角度
 * @returns 弧度
 */
function toRadians(degrees: number): number {
  return degrees * (Math.PI / 180);
}

/**
 * 弧度转角度
 * @param radians 弧度
 * @returns 角度
 */
function toDegrees(radians: number): number {
  return radians * (180 / Math.PI);
}

/**
 * 验证坐标是否在中国境内
 * @param coord 坐标点
 * @returns 是否在中国境内
 */
export function isCoordinateInChina(coord: Coordinate): boolean {
  // 粗略的中国边界检查
  const chinaBounds: BoundingBox = {
    west: 73,   // 最西端
    east: 135,  // 最东端
    south: 18,  // 最南端
    north: 54   // 最北端
  };
  
  return (
    coord.lng >= chinaBounds.west &&
    coord.lng <= chinaBounds.east &&
    coord.lat >= chinaBounds.south &&
    coord.lat <= chinaBounds.north
  );
}

/**
 * 计算位置集合的边界盒
 * @param locations 位置数组
 * @returns 边界盒
 */
export function calculateBoundingBox(locations: Location[]): BoundingBox {
  if (locations.length === 0) {
    throw new Error('位置数组不能为空');
  }
  
  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLng = Infinity;
  let maxLng = -Infinity;
  
  locations.forEach(location => {
    const { lat, lng } = location.coordinates;
    
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
    minLng = Math.min(minLng, lng);
    maxLng = Math.max(maxLng, lng);
  });
  
  return {
    west: minLng,
    south: minLat,
    east: maxLng,
    north: maxLat
  };
}

/**
 * 将地理坐标投影到屏幕坐标
 * @param coord 地理坐标
 * @param width 画布宽度
 * @param height 画布高度
 * @returns 屏幕坐标
 */
export function projectCoordinate(coord: Coordinate, width: number, height: number): ProjectedPoint {
  const projection = d3.geoMercator()
    .center(PROJECTION_CONFIG.center)
    .scale(PROJECTION_CONFIG.scale * Math.min(width, height) / 600) // 响应式缩放
    .translate([width / 2, height / 2]);
  
  const [x, y] = projection([coord.lng, coord.lat])!;
  return { x, y };
}

/**
 * 将屏幕坐标反投影到地理坐标
 * @param point 屏幕坐标
 * @param width 画布宽度
 * @param height 画布高度
 * @returns 地理坐标
 */
export function unprojectCoordinate(point: ProjectedPoint, width: number, height: number): Coordinate {
  const projection = d3.geoMercator()
    .center(PROJECTION_CONFIG.center)
    .scale(PROJECTION_CONFIG.scale * Math.min(width, height) / 600)
    .translate([width / 2, height / 2]);
  
  const [lng, lat] = projection.invert([point.x, point.y])!;
  return { lat, lng };
}

/**
 * 创建适合显示多个位置的投影
 * @param locations 位置数组
 * @param width 画布宽度
 * @param height 画布高度
 * @param padding 内边距
 * @returns 配置好的投影函数
 */
export function createAdaptiveProjection(
  locations: Location[],
  width: number,
  height: number,
  padding: number = 50
): d3.GeoProjection {
  if (locations.length === 0) {
    throw new Error('位置数组不能为空');
  }
  
  // 计算边界盒
  const bbox = calculateBoundingBox(locations);
  
  // 创建投影
  const projection = d3.geoMercator()
    .fitExtent(
      [[padding, padding], [width - padding, height - padding]],
      {
        type: 'Polygon',
        coordinates: [[
          [bbox.west, bbox.south],
          [bbox.east, bbox.south],
          [bbox.east, bbox.north],
          [bbox.west, bbox.north],
          [bbox.west, bbox.south]
        ]]
      }
    );
  
  return projection;
}

/**
 * 计算两点间的方位角（从北顺时针角度）
 * @param from 起始点
 * @param to 目标点
 * @returns 方位角（度）
 */
export function calculateBearing(from: Coordinate, to: Coordinate): number {
  const dLng = toRadians(to.lng - from.lng);
  const lat1 = toRadians(from.lat);
  const lat2 = toRadians(to.lat);
  
  const y = Math.sin(dLng) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
  
  let bearing = toDegrees(Math.atan2(y, x));
  return (bearing + 360) % 360; // 转换为0-360度
}

/**
 * 验证坐标数据的合理性
 * @param coord 坐标点
 * @returns 验证结果
 */
export function validateCoordinate(coord: Coordinate): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  // 检查纬度范围
  if (coord.lat < -90 || coord.lat > 90) {
    errors.push(`纬度 ${coord.lat} 超出有效范围 (-90 到 90)`);
  }
  
  // 检查经度范围
  if (coord.lng < -180 || coord.lng > 180) {
    errors.push(`经度 ${coord.lng} 超出有效范围 (-180 到 180)`);
  }
  
  // 检查是否是有效数字
  if (isNaN(coord.lat) || isNaN(coord.lng)) {
    errors.push('坐标包含非数字值');
  }
  
  // 检查是否在中国境内（可选）
  if (!isCoordinateInChina(coord)) {
    console.warn(`坐标 (${coord.lat}, ${coord.lng}) 不在中国境内`);
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
}
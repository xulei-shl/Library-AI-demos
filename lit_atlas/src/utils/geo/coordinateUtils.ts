/**
 * 地理坐标工具函数
 * 统一地理投影、边界盒计算与误差校验逻辑
 * 参考：@docs/design/data_orchestrator_20251215.md
 */

import { Coordinate, Location } from '../../core/data/normalizers';

/**
 * 边界盒类型定义
 */
export interface BoundingBox {
  west: number;  // 最西经度
  east: number;  // 最东经度
  south: number; // 最南纬度
  north: number; // 最北纬度
}

/**
 * 地球半径（千米）
 */
const EARTH_RADIUS_KM = 6371;

/**
 * 坐标验证容差（度）
 */
const COORDINATE_TOLERANCE = 0.0001;

/**
 * 计算两点之间的距离（Haversine公式）
 * @param coord1 起点坐标
 * @param coord2 终点坐标
 * @returns 距离（千米）
 */
export function calculateDistance(coord1: Coordinate, coord2: Coordinate): number {
  const lat1Rad = (coord1.lat * Math.PI) / 180;
  const lat2Rad = (coord2.lat * Math.PI) / 180;
  const deltaLat = ((coord2.lat - coord1.lat) * Math.PI) / 180;
  const deltaLng = ((coord2.lng - coord1.lng) * Math.PI) / 180;

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1Rad) * Math.cos(lat2Rad) * Math.sin(deltaLng / 2) * Math.sin(deltaLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return EARTH_RADIUS_KM * c;
}

/**
 * 计算多个坐标点的边界盒
 * @param coordinates 坐标数组
 * @param padding 边界盒扩展比例（0-1）
 * @returns 边界盒
 */
export function calculateBoundingBox(
  coordinates: Coordinate[],
  padding: number = 0.1
): BoundingBox {
  if (coordinates.length === 0) {
    throw new Error('坐标数组不能为空');
  }

  const lats = coordinates.map((c) => c.lat);
  const lngs = coordinates.map((c) => c.lng);

  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  // 计算扩展量
  const latPadding = (maxLat - minLat) * padding;
  const lngPadding = (maxLng - minLng) * padding;

  return {
    west: minLng - lngPadding,
    east: maxLng + lngPadding,
    south: minLat - latPadding,
    north: maxLat + latPadding,
  };
}

/**
 * 计算边界盒的中心点
 * @param bbox 边界盒
 * @returns 中心点坐标
 */
export function getBoundingBoxCenter(bbox: BoundingBox): Coordinate {
  return {
    lat: (bbox.north + bbox.south) / 2,
    lng: (bbox.east + bbox.west) / 2,
  };
}

/**
 * 计算边界盒的跨度（度）
 * @param bbox 边界盒
 * @returns 跨度 { latSpan, lngSpan }
 */
export function getBoundingBoxSpan(bbox: BoundingBox): { latSpan: number; lngSpan: number } {
  return {
    latSpan: bbox.north - bbox.south,
    lngSpan: bbox.east - bbox.west,
  };
}

/**
 * 验证坐标是否有效
 * @param coord 坐标
 * @returns 是否有效
 */
export function isValidCoordinate(coord: Coordinate): boolean {
  return (
    coord.lat >= -90 &&
    coord.lat <= 90 &&
    coord.lng >= -180 &&
    coord.lng <= 180 &&
    !isNaN(coord.lat) &&
    !isNaN(coord.lng)
  );
}

/**
 * 验证边界盒是否有效
 * @param bbox 边界盒
 * @returns 是否有效
 */
export function isValidBoundingBox(bbox: BoundingBox): boolean {
  return (
    bbox.west >= -180 &&
    bbox.east <= 180 &&
    bbox.south >= -90 &&
    bbox.north <= 90 &&
    bbox.west < bbox.east &&
    bbox.south < bbox.north
  );
}

/**
 * 检查坐标是否在边界盒内
 * @param coord 坐标
 * @param bbox 边界盒
 * @returns 是否在边界盒内
 */
export function isCoordinateInBoundingBox(coord: Coordinate, bbox: BoundingBox): boolean {
  return (
    coord.lng >= bbox.west &&
    coord.lng <= bbox.east &&
    coord.lat >= bbox.south &&
    coord.lat <= bbox.north
  );
}

/**
 * 合并多个边界盒
 * @param bboxes 边界盒数组
 * @returns 合并后的边界盒
 */
export function mergeBoundingBoxes(bboxes: BoundingBox[]): BoundingBox {
  if (bboxes.length === 0) {
    throw new Error('边界盒数组不能为空');
  }

  return {
    west: Math.min(...bboxes.map((b) => b.west)),
    east: Math.max(...bboxes.map((b) => b.east)),
    south: Math.min(...bboxes.map((b) => b.south)),
    north: Math.max(...bboxes.map((b) => b.north)),
  };
}

/**
 * 计算边界盒的面积（平方度）
 * @param bbox 边界盒
 * @returns 面积
 */
export function getBoundingBoxArea(bbox: BoundingBox): number {
  const { latSpan, lngSpan } = getBoundingBoxSpan(bbox);
  return latSpan * lngSpan;
}

/**
 * 将边界盒转换为坐标数组（四个角点）
 * @param bbox 边界盒
 * @returns 坐标数组
 */
export function boundingBoxToCoordinates(bbox: BoundingBox): Coordinate[] {
  return [
    { lat: bbox.south, lng: bbox.west }, // 西南
    { lat: bbox.north, lng: bbox.west }, // 西北
    { lat: bbox.north, lng: bbox.east }, // 东北
    { lat: bbox.south, lng: bbox.east }, // 东南
  ];
}

/**
 * 格式化坐标为字符串
 * @param coord 坐标
 * @param precision 精度（小数位数）
 * @returns 格式化字符串
 */
export function formatCoordinate(coord: Coordinate, precision: number = 4): string {
  return `${coord.lat.toFixed(precision)}, ${coord.lng.toFixed(precision)}`;
}

/**
 * 解析坐标字符串
 * @param coordStr 坐标字符串（格式：lat, lng）
 * @returns 坐标对象
 */
export function parseCoordinate(coordStr: string): Coordinate | null {
  const parts = coordStr.split(',').map((s) => s.trim());
  
  if (parts.length !== 2) {
    return null;
  }

  const lat = parseFloat(parts[0]);
  const lng = parseFloat(parts[1]);

  if (isNaN(lat) || isNaN(lng)) {
    return null;
  }

  const coord = { lat, lng };
  return isValidCoordinate(coord) ? coord : null;
}

/**
 * 计算两个坐标是否相等（考虑容差）
 * @param coord1 坐标1
 * @param coord2 坐标2
 * @param tolerance 容差（度）
 * @returns 是否相等
 */
export function areCoordinatesEqual(
  coord1: Coordinate,
  coord2: Coordinate,
  tolerance: number = COORDINATE_TOLERANCE
): boolean {
  return (
    Math.abs(coord1.lat - coord2.lat) < tolerance &&
    Math.abs(coord1.lng - coord2.lng) < tolerance
  );
}

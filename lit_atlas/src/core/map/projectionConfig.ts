/**
 * 地图投影配置模块
 * 定义 Natural Earth I 投影和相关参数
 */
import { geoNaturalEarth1, geoMercator, GeoProjection } from 'd3-geo';

/**
 * 投影类型枚举
 */
export enum ProjectionType {
  NATURAL_EARTH = 'naturalEarth',
  MERCATOR = 'mercator',
  EQUAL_EARTH = 'equalEarth'
}

/**
 * 投影配置接口
 */
export interface ProjectionConfig {
  type: ProjectionType;
  center: [number, number]; // [longitude, latitude]
  rotate: [number, number, number]; // [lambda, phi, gamma]
  scale: number;
  translate: [number, number]; // [x, y]
}

/**
 * 默认投影配置
 */
export const DEFAULT_PROJECTION_CONFIG: ProjectionConfig = {
  type: ProjectionType.NATURAL_EARTH,
  center: [0, 0],
  rotate: [0, 0, 0],
  scale: 160,
  translate: [400, 300] // 默认画布中心
};

/**
 * 创建 D3 投影对象
 * @param config 投影配置
 * @param width 画布宽度
 * @param height 画布高度
 * @returns D3 投影对象
 */
export function createProjection(
  config: ProjectionConfig,
  width: number,
  height: number
): GeoProjection {
  let projection: GeoProjection;

  // 根据类型创建投影
  switch (config.type) {
    case ProjectionType.NATURAL_EARTH:
      projection = geoNaturalEarth1();
      break;
    case ProjectionType.MERCATOR:
      projection = geoMercator();
      break;
    default:
      projection = geoNaturalEarth1();
  }

  // 应用配置
  projection
    .center(config.center)
    .rotate(config.rotate)
    .scale(config.scale)
    .translate([width / 2, height / 2]);

  return projection;
}

/**
 * 获取推荐的投影配置
 * @param viewType 视图类型
 * @returns 投影配置
 */
export function getRecommendedProjection(viewType: 'global' | 'regional' | 'local'): ProjectionConfig {
  switch (viewType) {
    case 'global':
      return {
        type: ProjectionType.NATURAL_EARTH,
        center: [0, 0],
        rotate: [0, 0, 0],
        scale: 160,
        translate: [400, 300]
      };
    case 'regional':
      return {
        type: ProjectionType.MERCATOR,
        center: [105, 35], // 中国中心
        rotate: [0, 0, 0],
        scale: 500,
        translate: [400, 300]
      };
    case 'local':
      return {
        type: ProjectionType.MERCATOR,
        center: [121.47, 31.23], // 上海
        rotate: [0, 0, 0],
        scale: 50000,
        translate: [400, 300]
      };
    default:
      return DEFAULT_PROJECTION_CONFIG;
  }
}

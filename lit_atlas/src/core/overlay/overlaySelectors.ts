/**
 * Overlay 数据选择器
 * 合并主副作者的路线和节点数据
 * 参考：@docs/design/overlay_mode_module_20251215.md
 */

import { Route } from '../data/normalizers';
import { MixedNodeData, MixedRouteData, AuthorRole } from './types';
import { ColorMixer } from './colorMixer';

/**
 * 简化的城市信息（用于 Overlay）
 */
interface CityInfo {
  id: string;
  name: string;
  coordinates: [number, number];
}

/**
 * 从 Route 提取城市信息
 */
function extractCities(route: Route): { from: CityInfo; to: CityInfo } {
  return {
    from: {
      id: route.start_location.name,
      name: route.start_location.name,
      coordinates: [route.start_location.coordinates.lng, route.start_location.coordinates.lat],
    },
    to: {
      id: route.end_location.name,
      name: route.end_location.name,
      coordinates: [route.end_location.coordinates.lng, route.end_location.coordinates.lat],
    },
  };
}

/**
 * 合并两位作者的节点数据
 */
export function mergeNodes(
  primaryRoutes: Route[],
  secondaryRoutes: Route[],
  colorMixer: ColorMixer
): MixedNodeData[] {
  const nodeMap = new Map<string, MixedNodeData>();

  // 处理主作者节点
  primaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    const year = route.year || 0;

    [from, to].forEach((city) => {
      if (!nodeMap.has(city.id)) {
        nodeMap.set(city.id, {
          cityId: city.id,
          cityName: city.name,
          coordinates: city.coordinates,
          hasPrimary: true,
          hasSecondary: false,
          primaryYear: year,
        });
      } else {
        const node = nodeMap.get(city.id)!;
        node.hasPrimary = true;
        if (!node.primaryYear || year < node.primaryYear) {
          node.primaryYear = year;
        }
      }
    });
  });

  // 处理副作者节点
  secondaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    const year = route.year || 0;

    [from, to].forEach((city) => {
      if (!nodeMap.has(city.id)) {
        nodeMap.set(city.id, {
          cityId: city.id,
          cityName: city.name,
          coordinates: city.coordinates,
          hasPrimary: false,
          hasSecondary: true,
          secondaryYear: year,
        });
      } else {
        const node = nodeMap.get(city.id)!;
        node.hasSecondary = true;
        if (!node.secondaryYear || year < node.secondaryYear) {
          node.secondaryYear = year;
        }
      }
    });
  });

  // 为共同节点生成混合颜色
  nodeMap.forEach((node) => {
    if (node.hasPrimary && node.hasSecondary) {
      node.mixedColor = colorMixer.getMixedColor(0.5);
    }
  });

  return Array.from(nodeMap.values());
}

/**
 * 合并两位作者的路线数据
 */
export function mergeRoutes(
  primaryRoutes: Route[],
  secondaryRoutes: Route[],
  primaryColor: string,
  secondaryColor: string
): MixedRouteData[] {
  const routes: MixedRouteData[] = [];

  // 主作者路线
  primaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    routes.push({
      id: `primary-${from.id}-${to.id}-${route.year || 0}`,
      role: AuthorRole.PRIMARY,
      from: from.id,
      to: to.id,
      year: route.year || 0,
      color: primaryColor,
    });
  });

  // 副作者路线
  secondaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    routes.push({
      id: `secondary-${from.id}-${to.id}-${route.year || 0}`,
      role: AuthorRole.SECONDARY,
      from: from.id,
      to: to.id,
      year: route.year || 0,
      color: secondaryColor,
    });
  });

  return routes;
}

/**
 * 查找共同访问的城市
 */
export function findCommonCities(
  primaryRoutes: Route[],
  secondaryRoutes: Route[]
): Set<string> {
  const primaryCities = new Set<string>();
  const secondaryCities = new Set<string>();

  primaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    primaryCities.add(from.id);
    primaryCities.add(to.id);
  });

  secondaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    secondaryCities.add(from.id);
    secondaryCities.add(to.id);
  });

  const common = new Set<string>();
  primaryCities.forEach((cityId) => {
    if (secondaryCities.has(cityId)) {
      common.add(cityId);
    }
  });

  return common;
}

/**
 * 计算两位作者的轨迹相似度（0-1）
 */
export function calculateSimilarity(
  primaryRoutes: Route[],
  secondaryRoutes: Route[]
): number {
  const commonCities = findCommonCities(primaryRoutes, secondaryRoutes);
  const allCities = new Set<string>();

  primaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    allCities.add(from.id);
    allCities.add(to.id);
  });

  secondaryRoutes.forEach((route) => {
    const { from, to } = extractCities(route);
    allCities.add(from.id);
    allCities.add(to.id);
  });

  if (allCities.size === 0) return 0;
  return commonCities.size / allCities.size;
}

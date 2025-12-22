/**
 * Feature Converter - 将应用数据转换为 OpenLayers Features
 */

import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import LineString from 'ol/geom/LineString';
import { fromLonLat } from 'ol/proj';
import type { Author, Work, Route } from '../../data/normalizers';

/**
 * Feature 类型
 */
export type FeatureType = 'city' | 'route';

/**
 * 城市 Feature 属性
 */
export interface CityFeatureProperties {
  type: 'city';
  name: string;
  coordinates: { lat: number; lng: number };
  works: Work[];
  routeCount: number;
}

/**
 * 路线 Feature 属性
 */
export interface RouteFeatureProperties {
  type: 'route';
  id: string;
  workId: string;
  workTitle: string;
  year?: number;
  startCity: string;
  endCity: string;
}

/**
 * 将作者数据转换为 OpenLayers Features
 */
export function convertAuthorToFeatures(author: Author | null): Feature[] {
  if (!author || !author.works) {
    return [];
  }

  const features: Feature[] = [];
  const citiesMap = new Map<string, CityFeatureProperties>();

  // 遍历所有作品和路线
  author.works.forEach((work: Work) => {
    work.routes.forEach((route: Route) => {
      // 收集城市信息
      const startCity = route.start_location.name;
      const endCity = route.end_location.name;

      // 起点城市
      if (!citiesMap.has(startCity)) {
        citiesMap.set(startCity, {
          type: 'city',
          name: startCity,
          coordinates: route.start_location.coordinates,
          works: [],
          routeCount: 0
        });
      }
      const startCityData = citiesMap.get(startCity)!;
      if (!startCityData.works.find(w => w.id === work.id)) {
        startCityData.works.push(work);
      }
      startCityData.routeCount++;

      // 终点城市
      if (!citiesMap.has(endCity)) {
        citiesMap.set(endCity, {
          type: 'city',
          name: endCity,
          coordinates: route.end_location.coordinates,
          works: [],
          routeCount: 0
        });
      }
      const endCityData = citiesMap.get(endCity)!;
      if (!endCityData.works.find(w => w.id === work.id)) {
        endCityData.works.push(work);
      }
      endCityData.routeCount++;

      // 创建路线 Feature
      const routeFeature = new Feature({
        geometry: new LineString([
          fromLonLat([
            route.start_location.coordinates.lng,
            route.start_location.coordinates.lat
          ]),
          fromLonLat([
            route.end_location.coordinates.lng,
            route.end_location.coordinates.lat
          ])
        ])
      });

      routeFeature.setProperties({
        type: 'route',
        id: route.id,
        workId: work.id,
        workTitle: work.title,
        year: route.year,
        startCity,
        endCity
      } as RouteFeatureProperties);

      features.push(routeFeature);
    });
  });

  // 创建城市 Features
  citiesMap.forEach((cityData) => {
    const cityFeature = new Feature({
      geometry: new Point(
        fromLonLat([cityData.coordinates.lng, cityData.coordinates.lat])
      )
    });

    cityFeature.setProperties(cityData);
    features.push(cityFeature);
  });

  console.info('[FeatureConverter] 转换完成:', {
    totalFeatures: features.length,
    cities: citiesMap.size,
    routes: features.filter(f => f.get('type') === 'route').length
  });

  return features;
}

/**
 * 获取 Feature 的类型
 */
export function getFeatureType(feature: Feature): FeatureType | null {
  return feature.get('type') as FeatureType | null;
}

/**
 * 判断是否为城市 Feature
 */
export function isCityFeature(feature: Feature): boolean {
  return getFeatureType(feature) === 'city';
}

/**
 * 判断是否为路线 Feature
 */
export function isRouteFeature(feature: Feature): boolean {
  return getFeatureType(feature) === 'route';
}

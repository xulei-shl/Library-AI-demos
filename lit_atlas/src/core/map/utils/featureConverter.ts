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
export type FeatureType = 'city' | 'route' | 'ripple';

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
 * 涟漪 Feature 属性
 */
export interface RippleFeatureProperties {
  type: 'ripple';
  name: string;
  coordinates: { lat: number; lng: number };
  year: number;
  workTitle: string;
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
  startYear?: number;
  endYear?: number;
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
    // 作品出版地涟漪 (如果有起点信息)
    // 注意：目前数据结构中 Work 没有直接的 location，通常隐含在 Route 的 start_location
    // 我们假设 Route 的 start_location 就是作品的出版地/起点

    const workYear = work.year || author.birth_year || 1900;

    work.routes.forEach((route: Route) => {
      // 收集城市信息
      const startCity = route.start_location.name;
      const endCity = route.end_location.name;
      const routeYear = route.year || workYear;

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
        year: routeYear,
        startYear: workYear,
        endYear: routeYear,
        startCity,
        endCity
      } as RouteFeatureProperties);

      features.push(routeFeature);

      // 创建起点涟漪 Feature
      const startRippleFeature = new Feature({
        geometry: new Point(
          fromLonLat([
            route.start_location.coordinates.lng,
            route.start_location.coordinates.lat
          ])
        )
      });
      startRippleFeature.setProperties({
        type: 'ripple',
        name: startCity,
        coordinates: route.start_location.coordinates,
        year: workYear,
        workTitle: work.title
      } as RippleFeatureProperties);
      features.push(startRippleFeature);

      // 创建终点涟漪 Feature
      const endRippleFeature = new Feature({
        geometry: new Point(
          fromLonLat([
            route.end_location.coordinates.lng,
            route.end_location.coordinates.lat
          ])
        )
      });
      endRippleFeature.setProperties({
        type: 'ripple',
        name: endCity,
        coordinates: route.end_location.coordinates,
        year: routeYear,
        workTitle: work.title
      } as RippleFeatureProperties);
      features.push(endRippleFeature);
    });
  });

  // 创建城市 Features (静态)
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
    routes: features.filter(f => f.get('type') === 'route').length,
    ripples: features.filter(f => f.get('type') === 'ripple').length
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

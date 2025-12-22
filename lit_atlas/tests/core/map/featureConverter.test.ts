/**
 * Feature Converter 单元测试
 */

import { convertAuthorToFeatures, isCityFeature, isRouteFeature } from '../../../src/core/map/utils/featureConverter';
import type { Author } from '../../../src/core/data/normalizers';

describe('FeatureConverter', () => {
  const mockAuthor: Author = {
    id: 'test-author',
    name: '测试作者',
    biography: '测试传记',
    works: [
      {
        id: 'work-1',
        title: '测试作品1',
        year: 1920,
        routes: [
          {
            id: 'route-1',
            start_location: {
              name: '北京',
              coordinates: { lat: 39.9, lng: 116.4 },
              bbox: [116.3, 39.8, 116.5, 40.0]
            },
            end_location: {
              name: '上海',
              coordinates: { lat: 31.2, lng: 121.5 },
              bbox: [121.4, 31.1, 121.6, 31.3]
            },
            year: 1920,
            collection_info: {
              has_collection: false
            }
          }
        ],
        metadata: {
          genre: '小说',
          themes: ['现代'],
          language: '中文'
        }
      }
    ]
  };

  describe('convertAuthorToFeatures', () => {
    it('应该返回空数组当作者为 null', () => {
      const features = convertAuthorToFeatures(null);
      expect(features).toEqual([]);
    });

    it('应该转换作者数据为 Features', () => {
      const features = convertAuthorToFeatures(mockAuthor);
      
      // 应该包含 1 条路线 + 2 个城市 = 3 个 Features
      expect(features.length).toBe(3);
    });

    it('应该创建城市 Features', () => {
      const features = convertAuthorToFeatures(mockAuthor);
      const cityFeatures = features.filter(f => f.get('type') === 'city');
      
      expect(cityFeatures.length).toBe(2);
      
      const beijing = cityFeatures.find(f => f.get('name') === '北京');
      expect(beijing).toBeDefined();
      expect(beijing?.get('coordinates')).toEqual({ lat: 39.9, lng: 116.4 });
    });

    it('应该创建路线 Features', () => {
      const features = convertAuthorToFeatures(mockAuthor);
      const routeFeatures = features.filter(f => f.get('type') === 'route');
      
      expect(routeFeatures.length).toBe(1);
      
      const route = routeFeatures[0];
      expect(route.get('workTitle')).toBe('测试作品1');
      expect(route.get('startCity')).toBe('北京');
      expect(route.get('endCity')).toBe('上海');
    });
  });

  describe('isCityFeature', () => {
    it('应该正确识别城市 Feature', () => {
      const features = convertAuthorToFeatures(mockAuthor);
      const cityFeature = features.find(f => f.get('type') === 'city');
      
      expect(isCityFeature(cityFeature!)).toBe(true);
    });

    it('应该正确识别非城市 Feature', () => {
      const features = convertAuthorToFeatures(mockAuthor);
      const routeFeature = features.find(f => f.get('type') === 'route');
      
      expect(isCityFeature(routeFeature!)).toBe(false);
    });
  });

  describe('isRouteFeature', () => {
    it('应该正确识别路线 Feature', () => {
      const features = convertAuthorToFeatures(mockAuthor);
      const routeFeature = features.find(f => f.get('type') === 'route');
      
      expect(isRouteFeature(routeFeature!)).toBe(true);
    });

    it('应该正确识别非路线 Feature', () => {
      const features = convertAuthorToFeatures(mockAuthor);
      const cityFeature = features.find(f => f.get('type') === 'city');
      
      expect(isRouteFeature(cityFeature!)).toBe(false);
    });
  });
});

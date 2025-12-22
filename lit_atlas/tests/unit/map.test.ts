/**
 * 地图模块单元测试
 * 测试 CameraController 和投影配置
 */
import { CameraController, AuthorBBox } from '../../src/core/map/cameraController';
import { createProjection, ProjectionType, getRecommendedProjection } from '../../src/core/map/projectionConfig';
import { BoundingBox } from '../../src/utils/geo/coordinateUtils';

describe('CameraController', () => {
  let controller: CameraController;

  beforeEach(() => {
    controller = new CameraController(800, 600, 50);
  });

  describe('初始化', () => {
    it('应该使用默认参数初始化', () => {
      const state = controller.getState();
      expect(state.center).toEqual([105, 35]);
      expect(state.zoom).toBe(1);
      expect(state.width).toBe(800);
      expect(state.height).toBe(600);
      expect(state.padding).toBe(50);
    });
  });

  describe('calculateSmartFlyTo', () => {
    it('应该计算正确的中心点', () => {
      const bbox: BoundingBox = {
        west: 100,
        east: 140,
        south: 20,
        north: 50
      };

      const params = controller.calculateSmartFlyTo(bbox, 0.1, 1000);

      expect(params.center[0]).toBe(120); // (100 + 140) / 2
      expect(params.center[1]).toBe(35);  // (20 + 50) / 2
      expect(params.duration).toBe(1000);
    });

    it('应该应用内边距百分比', () => {
      const bbox: BoundingBox = {
        west: 100,
        east: 140,
        south: 20,
        north: 50
      };

      const params1 = controller.calculateSmartFlyTo(bbox, 0.05, 1000);
      const params2 = controller.calculateSmartFlyTo(bbox, 0.2, 1000);

      // 更大的内边距应该导致更小的缩放级别（或相等，因为可能触及最小值）
      expect(params2.zoom).toBeLessThanOrEqual(params1.zoom);
    });

    it('应该限制最大和最小缩放级别', () => {
      const smallBbox: BoundingBox = {
        west: 120,
        east: 122,
        south: 30,
        north: 32
      };

      const params = controller.calculateSmartFlyTo(smallBbox, 0.1, 1000);

      expect(params.zoom).toBeGreaterThanOrEqual(0.5);
      expect(params.zoom).toBeLessThanOrEqual(10);
    });
  });

  describe('calculateAuthorBBox', () => {
    it('应该计算包含所有作品路线的边界盒', () => {
      const authorBBox: AuthorBBox = {
        west: 100,
        east: 140,
        south: 20,
        north: 50,
        works: [
          {
            id: 'work1',
            title: '作品1',
            routes: [
              { start: [121.47, 31.23], end: [139.69, 35.68] }
            ]
          },
          {
            id: 'work2',
            title: '作品2',
            routes: [
              { start: [116.40, 39.90], end: [126.97, 37.56] }
            ]
          }
        ]
      };

      const bbox = controller.calculateAuthorBBox(authorBBox);

      expect(bbox.west).toBeLessThan(116.40);
      expect(bbox.east).toBeGreaterThan(139.69);
      expect(bbox.south).toBeLessThan(31.23);
      expect(bbox.north).toBeGreaterThan(39.90);
    });

    it('应该添加缓冲区域', () => {
      const authorBBox: AuthorBBox = {
        west: 120,
        east: 122,
        south: 30,
        north: 32,
        works: [
          {
            id: 'work1',
            title: '作品1',
            routes: [
              { start: [121, 31], end: [121, 31] }
            ]
          }
        ]
      };

      const bbox = controller.calculateAuthorBBox(authorBBox);

      // 缓冲区应该扩大边界
      expect(bbox.west).toBeLessThan(120);
      expect(bbox.east).toBeGreaterThan(122);
      expect(bbox.south).toBeLessThan(30);
      expect(bbox.north).toBeGreaterThan(32);
    });
  });

  describe('坐标转换', () => {
    it('应该正确投影地理坐标到屏幕坐标', () => {
      const geoCoords: [number, number] = [121.47, 31.23]; // 上海
      const screenCoords = controller.project(geoCoords);

      expect(screenCoords).toHaveLength(2);
      expect(screenCoords[0]).toBeGreaterThan(0);
      expect(screenCoords[0]).toBeLessThan(800);
      expect(screenCoords[1]).toBeGreaterThan(0);
      expect(screenCoords[1]).toBeLessThan(600);
    });

    it('应该正确反投影屏幕坐标到地理坐标', () => {
      const screenCoords: [number, number] = [400, 300]; // 画布中心
      const geoCoords = controller.unproject(screenCoords);

      expect(geoCoords).not.toBeNull();
      expect(geoCoords).toHaveLength(2);
      if (geoCoords) {
        expect(geoCoords[0]).toBeGreaterThan(-180);
        expect(geoCoords[0]).toBeLessThan(180);
        expect(geoCoords[1]).toBeGreaterThan(-90);
        expect(geoCoords[1]).toBeLessThan(90);
      }
    });

    it('投影和反投影应该是可逆的', () => {
      const originalGeo: [number, number] = [121.47, 31.23];
      const screen = controller.project(originalGeo);
      const resultGeo = controller.unproject(screen);

      expect(resultGeo).not.toBeNull();
      if (resultGeo) {
        expect(resultGeo[0]).toBeCloseTo(originalGeo[0], 2);
        expect(resultGeo[1]).toBeCloseTo(originalGeo[1], 2);
      }
    });
  });

  describe('相机控制', () => {
    it('应该更新画布尺寸', () => {
      controller.setSize(1024, 768);
      const state = controller.getState();

      expect(state.width).toBe(1024);
      expect(state.height).toBe(768);
    });

    it('应该返回当前状态的副本', () => {
      const state1 = controller.getState();
      const state2 = controller.getState();

      expect(state1).toEqual(state2);
      expect(state1).not.toBe(state2); // 不同的对象引用
    });
  });
});

describe('投影配置', () => {
  describe('createProjection', () => {
    it('应该创建 Natural Earth 投影', () => {
      const projection = createProjection(
        {
          type: ProjectionType.NATURAL_EARTH,
          center: [0, 0],
          rotate: [0, 0, 0],
          scale: 160,
          translate: [400, 300]
        },
        800,
        600
      );

      expect(projection).toBeDefined();
      
      // 测试投影功能
      const coords = projection([0, 0]);
      expect(coords).toBeDefined();
      expect(coords).toHaveLength(2);
    });

    it('应该创建 Mercator 投影', () => {
      const projection = createProjection(
        {
          type: ProjectionType.MERCATOR,
          center: [105, 35],
          rotate: [0, 0, 0],
          scale: 500,
          translate: [400, 300]
        },
        800,
        600
      );

      expect(projection).toBeDefined();
    });
  });

  describe('getRecommendedProjection', () => {
    it('应该为全球视图返回 Natural Earth 投影', () => {
      const config = getRecommendedProjection('global');
      expect(config.type).toBe(ProjectionType.NATURAL_EARTH);
      expect(config.center).toEqual([0, 0]);
    });

    it('应该为区域视图返回 Mercator 投影', () => {
      const config = getRecommendedProjection('regional');
      expect(config.type).toBe(ProjectionType.MERCATOR);
      expect(config.scale).toBeGreaterThan(160);
    });

    it('应该为本地视图返回高缩放级别', () => {
      const config = getRecommendedProjection('local');
      expect(config.scale).toBeGreaterThan(1000);
    });
  });
});

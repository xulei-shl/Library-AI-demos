/**
 * 坐标工具函数测试
 * 参考：@docs/design/data_orchestrator_20251215.md
 */

import {
  calculateDistance,
  calculateBoundingBox,
  getBoundingBoxCenter,
  getBoundingBoxSpan,
  isValidCoordinate,
  isValidBoundingBox,
  isCoordinateInBoundingBox,
  mergeBoundingBoxes,
  getBoundingBoxArea,
  formatCoordinate,
  parseCoordinate,
  areCoordinatesEqual,
  Coordinate,
  BoundingBox
} from '../../../src/utils/geo/coordinateUtils';

describe('CoordinateUtils', () => {
  describe('calculateDistance', () => {
    it('应该计算两点之间的距离', () => {
      const beijing: Coordinate = { lat: 39.9042, lng: 116.4074 };
      const shanghai: Coordinate = { lat: 31.2304, lng: 121.4737 };

      const distance = calculateDistance(beijing, shanghai);

      // 北京到上海大约 1000+ 公里
      expect(distance).toBeGreaterThan(1000);
      expect(distance).toBeLessThan(1500);
    });

    it('应该返回 0 对于相同的点', () => {
      const coord: Coordinate = { lat: 39.9042, lng: 116.4074 };
      const distance = calculateDistance(coord, coord);

      expect(distance).toBe(0);
    });
  });

  describe('calculateBoundingBox', () => {
    it('应该计算多个坐标的边界盒', () => {
      const coordinates: Coordinate[] = [
        { lat: 39.9042, lng: 116.4074 }, // 北京
        { lat: 31.2304, lng: 121.4737 }, // 上海
        { lat: 22.3193, lng: 114.1694 }  // 香港
      ];

      const bbox = calculateBoundingBox(coordinates, 0);

      expect(bbox.west).toBeCloseTo(114.1694, 2);
      expect(bbox.east).toBeCloseTo(121.4737, 2);
      expect(bbox.south).toBeCloseTo(22.3193, 2);
      expect(bbox.north).toBeCloseTo(39.9042, 2);
    });

    it('应该应用 padding', () => {
      const coordinates: Coordinate[] = [
        { lat: 30, lng: 120 },
        { lat: 40, lng: 130 }
      ];

      const bboxNoPadding = calculateBoundingBox(coordinates, 0);
      const bboxWithPadding = calculateBoundingBox(coordinates, 0.1);

      expect(bboxWithPadding.west).toBeLessThan(bboxNoPadding.west);
      expect(bboxWithPadding.east).toBeGreaterThan(bboxNoPadding.east);
      expect(bboxWithPadding.south).toBeLessThan(bboxNoPadding.south);
      expect(bboxWithPadding.north).toBeGreaterThan(bboxNoPadding.north);
    });

    it('应该抛出错误对于空数组', () => {
      expect(() => calculateBoundingBox([])).toThrow('坐标数组不能为空');
    });
  });

  describe('getBoundingBoxCenter', () => {
    it('应该计算边界盒的中心点', () => {
      const bbox: BoundingBox = {
        west: 100,
        east: 120,
        south: 20,
        north: 40
      };

      const center = getBoundingBoxCenter(bbox);

      expect(center.lng).toBe(110);
      expect(center.lat).toBe(30);
    });
  });

  describe('getBoundingBoxSpan', () => {
    it('应该计算边界盒的跨度', () => {
      const bbox: BoundingBox = {
        west: 100,
        east: 120,
        south: 20,
        north: 40
      };

      const span = getBoundingBoxSpan(bbox);

      expect(span.lngSpan).toBe(20);
      expect(span.latSpan).toBe(20);
    });
  });

  describe('isValidCoordinate', () => {
    it('应该验证有效坐标', () => {
      expect(isValidCoordinate({ lat: 39.9042, lng: 116.4074 })).toBe(true);
      expect(isValidCoordinate({ lat: 0, lng: 0 })).toBe(true);
      expect(isValidCoordinate({ lat: -90, lng: -180 })).toBe(true);
      expect(isValidCoordinate({ lat: 90, lng: 180 })).toBe(true);
    });

    it('应该拒绝无效坐标', () => {
      expect(isValidCoordinate({ lat: 91, lng: 0 })).toBe(false);
      expect(isValidCoordinate({ lat: -91, lng: 0 })).toBe(false);
      expect(isValidCoordinate({ lat: 0, lng: 181 })).toBe(false);
      expect(isValidCoordinate({ lat: 0, lng: -181 })).toBe(false);
      expect(isValidCoordinate({ lat: NaN, lng: 0 })).toBe(false);
      expect(isValidCoordinate({ lat: 0, lng: NaN })).toBe(false);
    });
  });

  describe('isValidBoundingBox', () => {
    it('应该验证有效边界盒', () => {
      const validBbox: BoundingBox = {
        west: 100,
        east: 120,
        south: 20,
        north: 40
      };

      expect(isValidBoundingBox(validBbox)).toBe(true);
    });

    it('应该拒绝无效边界盒', () => {
      // west >= east
      expect(isValidBoundingBox({
        west: 120,
        east: 100,
        south: 20,
        north: 40
      })).toBe(false);

      // south >= north
      expect(isValidBoundingBox({
        west: 100,
        east: 120,
        south: 40,
        north: 20
      })).toBe(false);

      // 超出范围
      expect(isValidBoundingBox({
        west: -200,
        east: 120,
        south: 20,
        north: 40
      })).toBe(false);
    });
  });

  describe('isCoordinateInBoundingBox', () => {
    const bbox: BoundingBox = {
      west: 100,
      east: 120,
      south: 20,
      north: 40
    };

    it('应该判断坐标在边界盒内', () => {
      expect(isCoordinateInBoundingBox({ lat: 30, lng: 110 }, bbox)).toBe(true);
      expect(isCoordinateInBoundingBox({ lat: 20, lng: 100 }, bbox)).toBe(true);
      expect(isCoordinateInBoundingBox({ lat: 40, lng: 120 }, bbox)).toBe(true);
    });

    it('应该判断坐标在边界盒外', () => {
      expect(isCoordinateInBoundingBox({ lat: 10, lng: 110 }, bbox)).toBe(false);
      expect(isCoordinateInBoundingBox({ lat: 30, lng: 90 }, bbox)).toBe(false);
      expect(isCoordinateInBoundingBox({ lat: 50, lng: 110 }, bbox)).toBe(false);
      expect(isCoordinateInBoundingBox({ lat: 30, lng: 130 }, bbox)).toBe(false);
    });
  });

  describe('mergeBoundingBoxes', () => {
    it('应该合并多个边界盒', () => {
      const bbox1: BoundingBox = {
        west: 100,
        east: 110,
        south: 20,
        north: 30
      };

      const bbox2: BoundingBox = {
        west: 105,
        east: 120,
        south: 25,
        north: 40
      };

      const merged = mergeBoundingBoxes([bbox1, bbox2]);

      expect(merged.west).toBe(100);
      expect(merged.east).toBe(120);
      expect(merged.south).toBe(20);
      expect(merged.north).toBe(40);
    });

    it('应该抛出错误对于空数组', () => {
      expect(() => mergeBoundingBoxes([])).toThrow('边界盒数组不能为空');
    });
  });

  describe('getBoundingBoxArea', () => {
    it('应该计算边界盒面积', () => {
      const bbox: BoundingBox = {
        west: 100,
        east: 120,
        south: 20,
        north: 40
      };

      const area = getBoundingBoxArea(bbox);

      expect(area).toBe(20 * 20); // 400 平方度
    });
  });

  describe('formatCoordinate', () => {
    it('应该格式化坐标为字符串', () => {
      const coord: Coordinate = { lat: 39.9042, lng: 116.4074 };
      const formatted = formatCoordinate(coord, 2);

      expect(formatted).toBe('39.90, 116.41');
    });

    it('应该使用默认精度', () => {
      const coord: Coordinate = { lat: 39.9042, lng: 116.4074 };
      const formatted = formatCoordinate(coord);

      expect(formatted).toBe('39.9042, 116.4074');
    });
  });

  describe('parseCoordinate', () => {
    it('应该解析坐标字符串', () => {
      const coord = parseCoordinate('39.9042, 116.4074');

      expect(coord).not.toBeNull();
      expect(coord?.lat).toBeCloseTo(39.9042, 4);
      expect(coord?.lng).toBeCloseTo(116.4074, 4);
    });

    it('应该处理不同的空格', () => {
      const coord1 = parseCoordinate('39.9042,116.4074');
      const coord2 = parseCoordinate('39.9042,  116.4074');

      expect(coord1).not.toBeNull();
      expect(coord2).not.toBeNull();
    });

    it('应该返回 null 对于无效字符串', () => {
      expect(parseCoordinate('invalid')).toBeNull();
      expect(parseCoordinate('39.9042')).toBeNull();
      expect(parseCoordinate('abc, def')).toBeNull();
    });

    it('应该拒绝超出范围的坐标', () => {
      expect(parseCoordinate('91, 0')).toBeNull();
      expect(parseCoordinate('0, 181')).toBeNull();
    });
  });

  describe('areCoordinatesEqual', () => {
    it('应该判断坐标相等', () => {
      const coord1: Coordinate = { lat: 39.9042, lng: 116.4074 };
      const coord2: Coordinate = { lat: 39.9042, lng: 116.4074 };

      expect(areCoordinatesEqual(coord1, coord2)).toBe(true);
    });

    it('应该考虑容差', () => {
      const coord1: Coordinate = { lat: 39.9042, lng: 116.4074 };
      const coord2: Coordinate = { lat: 39.90421, lng: 116.40741 };

      expect(areCoordinatesEqual(coord1, coord2, 0.001)).toBe(true);
      expect(areCoordinatesEqual(coord1, coord2, 0.00001)).toBe(false);
    });

    it('应该判断坐标不相等', () => {
      const coord1: Coordinate = { lat: 39.9042, lng: 116.4074 };
      const coord2: Coordinate = { lat: 31.2304, lng: 121.4737 };

      expect(areCoordinatesEqual(coord1, coord2)).toBe(false);
    });
  });
});

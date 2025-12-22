/**
 * 相机控制器测试
 * 参考：@docs/design/narrative_map_canvas_20251215.md
 */

import { CameraController } from '../../../src/core/map/cameraController';
import { BoundingBox } from '../../../src/utils/geo/coordinateUtils';

describe('CameraController', () => {
  let controller: CameraController;
  const width = 800;
  const height = 600;
  const padding = 50;

  beforeEach(() => {
    controller = new CameraController(width, height, padding);
  });

  describe('初始化', () => {
    it('应该使用默认状态初始化', () => {
      const state = controller.getState();
      
      expect(state.center).toEqual([105, 35]); // 中国中心
      expect(state.zoom).toBe(1);
      expect(state.rotation).toEqual([0, 0, 0]);
      expect(state.width).toBe(width);
      expect(state.height).toBe(height);
      expect(state.padding).toBe(padding);
    });
  });

  describe('calculateSmartFlyTo', () => {
    it('应该计算正确的飞行参数', () => {
      const bbox: BoundingBox = {
        west: 116,
        east: 122,
        south: 31,
        north: 40
      };

      const params = controller.calculateSmartFlyTo(bbox, 0.1, 1000);

      // 验证中心点
      expect(params.center[0]).toBeCloseTo((116 + 122) / 2, 1);
      expect(params.center[1]).toBeCloseTo((31 + 40) / 2, 1);

      // 验证缩放级别
      expect(params.zoom).toBeGreaterThan(0);
      expect(params.zoom).toBeLessThanOrEqual(10);

      // 验证持续时间
      expect(params.duration).toBe(1000);
    });

    it('应该处理小范围边界盒', () => {
      const bbox: BoundingBox = {
        west: 121.4,
        east: 121.5,
        south: 31.2,
        north: 31.3
      };

      const params = controller.calculateSmartFlyTo(bbox, 0.1, 1000);

      // 小范围应该有更高的缩放级别
      expect(params.zoom).toBeGreaterThan(1);
    });

    it('应该处理大范围边界盒', () => {
      const bbox: BoundingBox = {
        west: 70,
        east: 140,
        south: 15,
        north: 55
      };

      const params = controller.calculateSmartFlyTo(bbox, 0.1, 1000);

      // 大范围应该有较低的缩放级别
      expect(params.zoom).toBeLessThan(2);
    });

    it('应该应用 padding 参数', () => {
      const bbox: BoundingBox = {
        west: 116,
        east: 122,
        south: 31,
        north: 40
      };

      const params1 = controller.calculateSmartFlyTo(bbox, 0.1, 1000);
      const params2 = controller.calculateSmartFlyTo(bbox, 0.3, 1000);

      // 更大的 padding 应该导致更小的缩放级别
      expect(params2.zoom).toBeLessThan(params1.zoom);
    });
  });

  describe('flyTo', () => {
    it('应该执行飞行动画', async () => {
      const targetCenter: [number, number] = [120, 30];
      const targetZoom = 2;
      const duration = 100;

      const updateCallback = jest.fn();

      await controller.flyTo(
        {
          center: targetCenter,
          zoom: targetZoom,
          duration
        },
        updateCallback
      );

      // 验证回调被调用
      expect(updateCallback).toHaveBeenCalled();

      // 验证最终状态
      const finalState = controller.getState();
      expect(finalState.center[0]).toBeCloseTo(targetCenter[0], 1);
      expect(finalState.center[1]).toBeCloseTo(targetCenter[1], 1);
      expect(finalState.zoom).toBeCloseTo(targetZoom, 1);
    });

    it('应该在动画期间多次调用更新回调', async () => {
      const updateCallback = jest.fn();

      await controller.flyTo(
        {
          center: [120, 30],
          zoom: 2,
          duration: 100
        },
        updateCallback
      );

      // 动画期间应该多次更新
      expect(updateCallback.mock.calls.length).toBeGreaterThan(1);
    });
  });

  describe('zoomTo', () => {
    it('应该缩放到指定级别', async () => {
      const targetZoom = 3;

      await controller.zoomTo(targetZoom, 100);

      const state = controller.getState();
      expect(state.zoom).toBeCloseTo(targetZoom, 1);
    });

    it('应该限制缩放范围', async () => {
      // 测试最小缩放
      await controller.zoomTo(0.1, 100);
      let state = controller.getState();
      expect(state.zoom).toBeGreaterThanOrEqual(0.5);

      // 测试最大缩放
      await controller.zoomTo(20, 100);
      state = controller.getState();
      expect(state.zoom).toBeLessThanOrEqual(10);
    });
  });

  describe('panTo', () => {
    it('应该平移到指定中心点', async () => {
      const targetCenter: [number, number] = [100, 25];

      await controller.panTo(targetCenter, 100);

      const state = controller.getState();
      expect(state.center[0]).toBeCloseTo(targetCenter[0], 1);
      expect(state.center[1]).toBeCloseTo(targetCenter[1], 1);
    });

    it('应该保持当前缩放级别', async () => {
      const initialZoom = controller.getState().zoom;
      
      await controller.panTo([100, 25], 100);

      const state = controller.getState();
      expect(state.zoom).toBe(initialZoom);
    });
  });

  describe('reset', () => {
    it('应该重置到默认状态', async () => {
      // 先改变状态
      await controller.flyTo({
        center: [120, 30],
        zoom: 5,
        duration: 100
      });

      // 重置
      await controller.reset(100);

      // 验证恢复到默认状态
      const state = controller.getState();
      expect(state.center).toEqual([105, 35]);
      expect(state.zoom).toBe(1);
    });
  });

  describe('setSize', () => {
    it('应该更新视口尺寸', () => {
      const newWidth = 1024;
      const newHeight = 768;

      controller.setSize(newWidth, newHeight);

      const state = controller.getState();
      expect(state.width).toBe(newWidth);
      expect(state.height).toBe(newHeight);
    });
  });

  describe('project 和 unproject', () => {
    it('应该正确转换坐标', () => {
      const geoCoord: [number, number] = [116.4074, 39.9042]; // 北京

      // 地理坐标 -> 屏幕坐标
      const screenCoord = controller.project(geoCoord);
      expect(screenCoord).toBeDefined();
      expect(screenCoord[0]).toBeGreaterThan(0);
      expect(screenCoord[1]).toBeGreaterThan(0);

      // 屏幕坐标 -> 地理坐标
      const unprojected = controller.unproject(screenCoord);
      expect(unprojected).toBeDefined();
      
      if (unprojected) {
        expect(unprojected[0]).toBeCloseTo(geoCoord[0], 0);
        expect(unprojected[1]).toBeCloseTo(geoCoord[1], 0);
      }
    });
  });
});

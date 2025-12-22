/**
 * 时间轴构建器测试
 */

import { TimelineBuilder } from '../../../src/core/scheduler/timelineBuilder';
import { Route } from '../../../src/core/data/normalizers';
import { SchedulerEventType } from '../../../src/core/scheduler/types';

describe('TimelineBuilder', () => {
  let builder: TimelineBuilder;

  beforeEach(() => {
    builder = new TimelineBuilder();
  });

  describe('buildTimeline', () => {
    it('应该为单条路线生成正确的事件序列', () => {
      const routes: Route[] = [
        {
          id: 'route-1',
          start_location: {
            name: '北京',
            coordinates: { lat: 39.9, lng: 116.4 },
          },
          end_location: {
            name: '上海',
            coordinates: { lat: 31.2, lng: 121.5 },
          },
          year: 1920,
          collection_info: { has_collection: false },
        },
      ];

      const events = builder.buildTimeline(routes, '#2c3e50');

      // 应该生成3个事件：LINE_START, LINE_COMPLETE, RIPPLE_TRIGGER
      expect(events).toHaveLength(3);
      expect(events[0].type).toBe(SchedulerEventType.LINE_START);
      expect(events[1].type).toBe(SchedulerEventType.LINE_COMPLETE);
      expect(events[2].type).toBe(SchedulerEventType.RIPPLE_TRIGGER);
    });

    it('应该按年份排序路线', () => {
      const routes: Route[] = [
        {
          id: 'route-2',
          start_location: {
            name: '上海',
            coordinates: { lat: 31.2, lng: 121.5 },
          },
          end_location: {
            name: '广州',
            coordinates: { lat: 23.1, lng: 113.3 },
          },
          year: 1930,
          collection_info: { has_collection: false },
        },
        {
          id: 'route-1',
          start_location: {
            name: '北京',
            coordinates: { lat: 39.9, lng: 116.4 },
          },
          end_location: {
            name: '上海',
            coordinates: { lat: 31.2, lng: 121.5 },
          },
          year: 1920,
          collection_info: { has_collection: false },
        },
      ];

      const events = builder.buildTimeline(routes, '#2c3e50');

      // 第一个LINE_START应该是1920年的路线
      const firstLineStart = events.find(e => e.type === SchedulerEventType.LINE_START);
      expect(firstLineStart?.routeId).toBe('route-1');
    });

    it('应该确保事件时间戳单调递增', () => {
      const routes: Route[] = [
        {
          id: 'route-1',
          start_location: {
            name: '北京',
            coordinates: { lat: 39.9, lng: 116.4 },
          },
          end_location: {
            name: '上海',
            coordinates: { lat: 31.2, lng: 121.5 },
          },
          year: 1920,
          collection_info: { has_collection: false },
        },
        {
          id: 'route-2',
          start_location: {
            name: '上海',
            coordinates: { lat: 31.2, lng: 121.5 },
          },
          end_location: {
            name: '广州',
            coordinates: { lat: 23.1, lng: 113.3 },
          },
          year: 1930,
          collection_info: { has_collection: false },
        },
      ];

      const events = builder.buildTimeline(routes, '#2c3e50');

      // 检查时间戳单调递增
      for (let i = 1; i < events.length; i++) {
        expect(events[i].timestamp).toBeGreaterThanOrEqual(events[i - 1].timestamp);
      }
    });

    it('应该为有馆藏的路线生成正确的涟漪事件', () => {
      const routes: Route[] = [
        {
          id: 'route-1',
          start_location: {
            name: '北京',
            coordinates: { lat: 39.9, lng: 116.4 },
          },
          end_location: {
            name: '上海',
            coordinates: { lat: 31.2, lng: 121.5 },
          },
          year: 1920,
          collection_info: {
            has_collection: true,
            collection_meta: {
              title: '测试馆藏',
              date: '1920-01-01',
              location: '上海图书馆',
            },
          },
        },
      ];

      const events = builder.buildTimeline(routes, '#2c3e50');

      const rippleEvent = events.find(e => e.type === SchedulerEventType.RIPPLE_TRIGGER);
      expect(rippleEvent).toBeDefined();
      expect(rippleEvent?.hasCollection).toBe(true);
      expect(rippleEvent?.collectionMeta).toBeDefined();
    });
  });

  describe('updateConfig', () => {
    it('应该能够更新配置', () => {
      builder.updateConfig({ baseDuration: 3000 });
      const config = builder.getConfig();
      expect(config.baseDuration).toBe(3000);
    });
  });
});

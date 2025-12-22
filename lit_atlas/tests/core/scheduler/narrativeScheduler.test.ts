/**
 * 叙事调度器测试
 */

import { NarrativeScheduler } from '../../../src/core/scheduler/narrativeScheduler';
import { Route } from '../../../src/core/data/normalizers';
import { SchedulerEventType, SchedulerState } from '../../../src/core/scheduler/types';

describe('NarrativeScheduler', () => {
  let scheduler: NarrativeScheduler;

  const mockRoutes: Route[] = [
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

  beforeEach(() => {
    scheduler = new NarrativeScheduler();
  });

  afterEach(() => {
    scheduler.dispose();
  });

  describe('load', () => {
    it('应该成功加载路线数据', async () => {
      await scheduler.load(mockRoutes);
      expect(scheduler.getState()).toBe(SchedulerState.READY);
    });

    it('应该发送SCHEDULER_READY事件', async () => {
      const events: any[] = [];
      scheduler.on((event) => events.push(event));

      await scheduler.load(mockRoutes);

      const readyEvent = events.find(e => e.type === SchedulerEventType.SCHEDULER_READY);
      expect(readyEvent).toBeDefined();
      expect(readyEvent.data.totalEvents).toBeGreaterThan(0);
    });
  });

  describe('play/pause/stop', () => {
    beforeEach(async () => {
      await scheduler.load(mockRoutes);
    });

    it('应该能够开始播放', () => {
      scheduler.play();
      expect(scheduler.getState()).toBe(SchedulerState.PLAYING);
    });

    it('应该能够暂停播放', () => {
      scheduler.play();
      scheduler.pause();
      expect(scheduler.getState()).toBe(SchedulerState.PAUSED);
    });

    it('应该能够停止播放', () => {
      scheduler.play();
      scheduler.stop();
      expect(scheduler.getState()).toBe(SchedulerState.READY);
      expect(scheduler.getCurrentTime()).toBe(0);
    });

    it('暂停后不应该触发新事件', (done) => {
      const events: any[] = [];
      scheduler.on((event) => events.push(event));

      scheduler.play();
      
      setTimeout(() => {
        const eventCountBeforePause = events.length;
        scheduler.pause();
        
        setTimeout(() => {
          // 暂停后事件数量不应该增加（除了PAUSE事件本身）
          const pauseEvents = events.filter(e => e.type === SchedulerEventType.PLAYBACK_PAUSE);
          expect(events.length - eventCountBeforePause).toBeLessThanOrEqual(pauseEvents.length);
          done();
        }, 100);
      }, 50);
    });
  });

  describe('seek', () => {
    beforeEach(async () => {
      await scheduler.load(mockRoutes);
    });

    it('应该能够跳转到指定时间', () => {
      const targetTime = 1000;
      scheduler.seek(targetTime);
      expect(scheduler.getCurrentTime()).toBe(targetTime);
    });

    it('应该限制跳转时间在有效范围内', () => {
      const totalDuration = scheduler.getTotalDuration();
      
      scheduler.seek(-100);
      expect(scheduler.getCurrentTime()).toBe(0);
      
      scheduler.seek(totalDuration + 1000);
      expect(scheduler.getCurrentTime()).toBe(totalDuration);
    });

    it('应该发送PLAYBACK_SEEK事件', () => {
      const events: any[] = [];
      scheduler.on((event) => events.push(event));

      scheduler.seek(1000);

      const seekEvent = events.find(e => e.type === SchedulerEventType.PLAYBACK_SEEK);
      expect(seekEvent).toBeDefined();
    });
  });

  describe('setSpeed', () => {
    beforeEach(async () => {
      await scheduler.load(mockRoutes);
    });

    it('应该能够设置播放速度', () => {
      scheduler.setSpeed(2.0);
      // 速度变化应该通过事件反映
      const events: any[] = [];
      scheduler.on((event) => events.push(event));
      
      scheduler.setSpeed(1.5);
      
      const speedEvent = events.find(e => e.type === SchedulerEventType.PLAYBACK_SPEED_CHANGE);
      expect(speedEvent).toBeDefined();
      expect(speedEvent.data.speed).toBe(1.5);
    });

    it('应该限制速度在有效范围内', () => {
      const events: any[] = [];
      scheduler.on((event) => events.push(event));

      scheduler.setSpeed(0.1);
      let speedEvent = events.find(e => e.type === SchedulerEventType.PLAYBACK_SPEED_CHANGE);
      expect(speedEvent.data.speed).toBeGreaterThanOrEqual(0.25);

      events.length = 0;
      scheduler.setSpeed(5.0);
      speedEvent = events.find(e => e.type === SchedulerEventType.PLAYBACK_SPEED_CHANGE);
      expect(speedEvent.data.speed).toBeLessThanOrEqual(3.0);
    });
  });

  describe('getProgress', () => {
    beforeEach(async () => {
      await scheduler.load(mockRoutes);
    });

    it('应该返回正确的播放进度', () => {
      expect(scheduler.getProgress()).toBe(0);
      
      const halfTime = scheduler.getTotalDuration() / 2;
      scheduler.seek(halfTime);
      expect(scheduler.getProgress()).toBeCloseTo(0.5, 1);
    });
  });

  describe('dispose', () => {
    it('应该清理所有资源', async () => {
      await scheduler.load(mockRoutes);
      scheduler.play();
      scheduler.dispose();
      
      expect(scheduler.getState()).toBe(SchedulerState.IDLE);
    });
  });
});

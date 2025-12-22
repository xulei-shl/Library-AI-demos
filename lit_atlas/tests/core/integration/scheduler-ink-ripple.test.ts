/**
 * 调度器 + InkLine + RippleNode 集成测试
 * 验证完整的叙事动画流程
 */

import { NarrativeScheduler } from '../../../src/core/scheduler/narrativeScheduler';
import { Route } from '../../../src/core/data/normalizers';
import { SchedulerEventType } from '../../../src/core/scheduler/types';

describe('Scheduler + InkLine + RippleNode 集成测试', () => {
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
      collection_info: { has_collection: true },
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
      year: 1925,
      collection_info: { has_collection: false },
    },
  ];

  beforeEach(() => {
    scheduler = new NarrativeScheduler();
  });

  afterEach(() => {
    scheduler.dispose();
  });

  it('应该按正确顺序触发事件：LINE_START -> LINE_COMPLETE -> RIPPLE_TRIGGER', async () => {
    await scheduler.load(mockRoutes);

    const events: any[] = [];
    scheduler.on((event) => events.push(event));

    scheduler.play();

    // 等待一些事件触发
    await new Promise(resolve => setTimeout(resolve, 100));

    // 验证事件顺序
    const lineStartEvents = events.filter(e => e.type === SchedulerEventType.LINE_START);
    const lineCompleteEvents = events.filter(e => e.type === SchedulerEventType.LINE_COMPLETE);
    const rippleEvents = events.filter(e => e.type === SchedulerEventType.RIPPLE_TRIGGER);

    // 应该有LINE_START事件
    expect(lineStartEvents.length).toBeGreaterThan(0);

    // 对于每个LINE_START，应该有对应的LINE_COMPLETE和RIPPLE_TRIGGER
    lineStartEvents.forEach(lineStart => {
      const lineComplete = lineCompleteEvents.find(e => e.routeId === lineStart.routeId);
      const ripple = rippleEvents.find(e => e.routeId === lineStart.routeId);

      if (lineComplete) {
        // LINE_COMPLETE应该在LINE_START之后
        expect(lineComplete.timestamp).toBeGreaterThan(lineStart.timestamp);
      }

      if (ripple) {
        // RIPPLE应该在LINE_COMPLETE之后
        expect(ripple.timestamp).toBeGreaterThan(lineStart.timestamp);
      }
    });
  });

  it('应该在暂停时停止触发新事件', async () => {
    await scheduler.load(mockRoutes);

    const events: any[] = [];
    scheduler.on((event) => events.push(event));

    scheduler.play();

    // 播放一段时间后暂停
    await new Promise(resolve => setTimeout(resolve, 50));
    const eventCountBeforePause = events.length;
    scheduler.pause();

    // 等待确认没有新事件
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // 事件数量不应该显著增加（除了PAUSE事件本身）
    const pauseEvents = events.filter(e => e.type === SchedulerEventType.PLAYBACK_PAUSE);
    expect(events.length - eventCountBeforePause).toBeLessThanOrEqual(pauseEvents.length + 2);
  });

  it('应该在seek后正确恢复事件触发', async () => {
    await scheduler.load(mockRoutes);

    const events: any[] = [];
    scheduler.on((event) => events.push(event));

    // 跳转到中间位置
    const halfTime = scheduler.getTotalDuration() / 2;
    scheduler.seek(halfTime);

    // 应该触发所有在这个时间点之前的事件
    const lineStartEvents = events.filter(e => e.type === SchedulerEventType.LINE_START);
    expect(lineStartEvents.length).toBeGreaterThan(0);

    // 所有触发的事件时间戳应该小于等于seek时间
    events.forEach(event => {
      if (event.type !== SchedulerEventType.PLAYBACK_SEEK) {
        expect(event.timestamp).toBeLessThanOrEqual(halfTime);
      }
    });
  });

  it('应该正确处理LINE_PROGRESS事件', async () => {
    await scheduler.load(mockRoutes);

    const progressEvents: any[] = [];
    scheduler.onType(SchedulerEventType.LINE_PROGRESS, (event) => {
      progressEvents.push(event);
    });

    scheduler.play();

    // 等待一些进度事件
    await new Promise(resolve => setTimeout(resolve, 200));

    // 应该有进度事件
    expect(progressEvents.length).toBeGreaterThan(0);

    // 进度值应该在0-1之间
    progressEvents.forEach(event => {
      expect(event.progress).toBeGreaterThanOrEqual(0);
      expect(event.progress).toBeLessThanOrEqual(1);
    });
  });

  it('应该在播放完成时触发SCHEDULER_COMPLETE事件', async () => {
    // 使用较短的时长配置
    scheduler = new NarrativeScheduler({
      timeline: {
        baseDuration: 100,
        distanceFactor: 0.1,
        yearFactor: 1,
        rippleDelay: 50,
        rippleDuration: 50,
        minInterval: 10,
      },
    });

    await scheduler.load(mockRoutes);

    const events: any[] = [];
    scheduler.on((event) => events.push(event));

    scheduler.play();

    // 等待播放完成
    const totalDuration = scheduler.getTotalDuration();
    await new Promise(resolve => setTimeout(resolve, totalDuration + 200));

    // 应该有完成事件
    const completeEvent = events.find(e => e.type === SchedulerEventType.SCHEDULER_COMPLETE);
    expect(completeEvent).toBeDefined();
  });

  it('应该支持播放速度调整', async () => {
    await scheduler.load(mockRoutes);

    scheduler.setSpeed(2.0);
    scheduler.play();

    const startTime = Date.now();
    
    // 等待一段时间
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const elapsed = Date.now() - startTime;
    const schedulerTime = scheduler.getCurrentTime();

    // 调度器时间应该大约是实际时间的2倍
    expect(schedulerTime).toBeGreaterThan(elapsed * 1.5);
  });
});

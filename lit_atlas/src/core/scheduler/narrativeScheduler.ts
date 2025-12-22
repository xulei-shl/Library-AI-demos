/**
 * 叙事调度器核心
 * 负责事件队列的执行、播放控制和状态管理
 * 参考：@docs/design/narrative_scheduler_20251215.md
 */

import { Subject, Subscription } from 'rxjs';
import { Route } from '../data/normalizers';
import { TimelineBuilder } from './timelineBuilder';
import {
  SchedulerEvent,
  SchedulerEventType,
  SchedulerState,
  SchedulerConfig,
  DEFAULT_SCHEDULER_CONFIG,
  LineProgressEvent,
} from './types';

/**
 * 叙事调度器类
 */
export class NarrativeScheduler {
  // 配置
  private config: SchedulerConfig;
  
  // 状态
  private state: SchedulerState = SchedulerState.IDLE;
  private events: SchedulerEvent[] = [];
  private currentEventIndex: number = 0;
  private currentTime: number = 0;
  private totalDuration: number = 0;
  private playbackSpeed: number = 1.0;
  
  // 时间控制
  private startTimestamp: number = 0;
  private pausedTime: number = 0;
  private animationFrameId: number | null = null;
  
  // 事件总线
  private eventBus = new Subject<SchedulerEvent>();
  private subscriptions: Subscription[] = [];
  
  // 时间轴构建器
  private timelineBuilder: TimelineBuilder;
  
  // 活跃的线条进度追踪
  private activeLines = new Map<string, { startTime: number; duration: number }>();

  constructor(config: Partial<SchedulerConfig> = {}) {
    this.config = { ...DEFAULT_SCHEDULER_CONFIG, ...config };
    this.timelineBuilder = new TimelineBuilder(this.config.timeline);
    
    if (this.config.enableLogging) {
      console.info('叙事调度器初始化完成', this.config);
    }
  }

  /**
   * 加载路线数据并构建时间轴
   */
  async load(routes: Route[], authorColor: string = '#2c3e50'): Promise<void> {
    this.setState(SchedulerState.LOADING);
    
    try {
      // 构建时间轴
      this.events = this.timelineBuilder.buildTimeline(routes, authorColor);
      this.totalDuration = this.calculateTotalDuration();
      
      // 重置状态
      this.currentEventIndex = 0;
      this.currentTime = 0;
      this.pausedTime = 0;
      this.activeLines.clear();
      
      this.setState(SchedulerState.READY);
      
      // 发送就绪事件
      this.emit({
        id: `scheduler-ready-${Date.now()}`,
        type: SchedulerEventType.SCHEDULER_READY,
        timestamp: 0,
        duration: 0,
        data: {
          totalEvents: this.events.length,
          totalDuration: this.totalDuration,
        },
      });
      
      if (this.config.enableLogging) {
        console.info(`调度器加载完成: ${this.events.length} 个事件, 总时长 ${this.totalDuration}ms`);
      }
    } catch (error) {
      this.setState(SchedulerState.ERROR);
      this.emit({
        id: `scheduler-error-${Date.now()}`,
        type: SchedulerEventType.SCHEDULER_ERROR,
        timestamp: 0,
        duration: 0,
        data: {
          error: error instanceof Error ? error.message : '未知错误',
        },
      });
      throw error;
    }
  }

  /**
   * 开始播放
   */
  play(): void {
    if (this.state === SchedulerState.PLAYING) {
      console.warn('调度器已在播放中');
      return;
    }
    
    if (this.state !== SchedulerState.READY && this.state !== SchedulerState.PAUSED) {
      console.warn('调度器未就绪，无法播放');
      return;
    }
    
    this.setState(SchedulerState.PLAYING);
    this.startTimestamp = performance.now() - this.pausedTime;
    this.startPlaybackLoop();
    
    this.emit({
      id: `playback-play-${Date.now()}`,
      type: SchedulerEventType.PLAYBACK_PLAY,
      timestamp: this.currentTime,
      duration: 0,
    });
    
    if (this.config.enableLogging) {
      console.info('开始播放');
    }
  }

  /**
   * 暂停播放
   */
  pause(): void {
    if (this.state !== SchedulerState.PLAYING) {
      console.warn('调度器未在播放中');
      return;
    }
    
    this.setState(SchedulerState.PAUSED);
    this.pausedTime = performance.now() - this.startTimestamp;
    this.stopPlaybackLoop();
    
    this.emit({
      id: `playback-pause-${Date.now()}`,
      type: SchedulerEventType.PLAYBACK_PAUSE,
      timestamp: this.currentTime,
      duration: 0,
    });
    
    if (this.config.enableLogging) {
      console.info('暂停播放');
    }
  }

  /**
   * 停止播放
   */
  stop(): void {
    this.setState(SchedulerState.READY);
    this.stopPlaybackLoop();
    this.currentTime = 0;
    this.pausedTime = 0;
    this.currentEventIndex = 0;
    this.activeLines.clear();
    
    this.emit({
      id: `playback-stop-${Date.now()}`,
      type: SchedulerEventType.PLAYBACK_STOP,
      timestamp: 0,
      duration: 0,
    });
    
    if (this.config.enableLogging) {
      console.info('停止播放');
    }
  }

  /**
   * 跳转到指定时间
   */
  seek(time: number): void {
    const clampedTime = Math.max(0, Math.min(time, this.totalDuration));
    const wasPlaying = this.state === SchedulerState.PLAYING;
    
    if (wasPlaying) {
      this.pause();
    }
    
    this.setState(SchedulerState.SEEKING);
    this.currentTime = clampedTime;
    this.pausedTime = clampedTime;
    
    // 重新计算当前事件索引
    this.currentEventIndex = this.findEventIndexAtTime(clampedTime);
    
    // 清除活跃线条并重新触发当前时间点的事件
    this.activeLines.clear();
    this.triggerEventsAtTime(clampedTime);
    
    this.emit({
      id: `playback-seek-${Date.now()}`,
      type: SchedulerEventType.PLAYBACK_SEEK,
      timestamp: clampedTime,
      duration: 0,
      data: { seekTime: clampedTime },
    });
    
    if (wasPlaying) {
      this.setState(SchedulerState.PAUSED);
      // 不自动恢复播放，等待用户操作
    } else {
      this.setState(SchedulerState.READY);
    }
    
    if (this.config.enableLogging) {
      console.info(`跳转到时间: ${clampedTime}ms`);
    }
  }

  /**
   * 设置播放速度
   */
  setSpeed(speed: number): void {
    const clampedSpeed = Math.max(0.25, Math.min(speed, 3.0));
    this.playbackSpeed = clampedSpeed;
    
    // 如果正在播放，需要调整时间基准
    if (this.state === SchedulerState.PLAYING) {
      this.pausedTime = performance.now() - this.startTimestamp;
      this.startTimestamp = performance.now() - this.pausedTime;
    }
    
    this.emit({
      id: `playback-speed-${Date.now()}`,
      type: SchedulerEventType.PLAYBACK_SPEED_CHANGE,
      timestamp: this.currentTime,
      duration: 0,
      data: { speed: clampedSpeed },
    });
    
    if (this.config.enableLogging) {
      console.info(`设置播放速度: ${clampedSpeed}x`);
    }
  }

  /**
   * 订阅事件
   */
  on(callback: (event: SchedulerEvent) => void): Subscription {
    const subscription = this.eventBus.subscribe(callback);
    this.subscriptions.push(subscription);
    return subscription;
  }

  /**
   * 订阅特定类型的事件
   */
  onType(type: SchedulerEventType, callback: (event: SchedulerEvent) => void): Subscription {
    const subscription = this.eventBus.subscribe((event) => {
      if (event.type === type) {
        callback(event);
      }
    });
    this.subscriptions.push(subscription);
    return subscription;
  }

  /**
   * 获取当前状态
   */
  getState(): SchedulerState {
    return this.state;
  }

  /**
   * 获取当前时间
   */
  getCurrentTime(): number {
    return this.currentTime;
  }

  /**
   * 获取总时长
   */
  getTotalDuration(): number {
    return this.totalDuration;
  }

  /**
   * 获取播放进度（0-1）
   */
  getProgress(): number {
    if (this.totalDuration === 0) return 0;
    return Math.max(0, Math.min(1, this.currentTime / this.totalDuration));
  }

  /**
   * 销毁调度器
   */
  dispose(): void {
    this.stopPlaybackLoop();
    this.subscriptions.forEach(sub => sub.unsubscribe());
    this.subscriptions = [];
    this.eventBus.complete();
    this.activeLines.clear();
    this.events = [];
    this.setState(SchedulerState.IDLE);
    
    if (this.config.enableLogging) {
      console.info('调度器已销毁');
    }
  }

  // ========== 私有方法 ==========

  /**
   * 播放循环
   */
  private startPlaybackLoop(): void {
    const tick = () => {
      if (this.state !== SchedulerState.PLAYING) {
        return;
      }
      
      // 计算当前时间
      const elapsed = (performance.now() - this.startTimestamp) * this.playbackSpeed;
      this.currentTime = elapsed;
      
      // 处理事件
      this.processEvents();
      
      // 更新活跃线条的进度
      this.updateLineProgress();
      
      // 检查是否完成
      if (this.currentTime >= this.totalDuration) {
        this.handlePlaybackComplete();
        return;
      }
      
      // 继续循环
      this.animationFrameId = requestAnimationFrame(tick);
    };
    
    this.animationFrameId = requestAnimationFrame(tick);
  }

  /**
   * 停止播放循环
   */
  private stopPlaybackLoop(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  /**
   * 处理事件队列
   */
  private processEvents(): void {
    while (this.currentEventIndex < this.events.length) {
      const event = this.events[this.currentEventIndex];
      
      if (event.timestamp > this.currentTime) {
        break;
      }
      
      // 触发事件
      this.triggerEvent(event);
      this.currentEventIndex++;
    }
  }

  /**
   * 触发单个事件
   */
  private triggerEvent(event: SchedulerEvent): void {
    // 记录线条开始事件
    if (event.type === SchedulerEventType.LINE_START) {
      this.activeLines.set(event.routeId, {
        startTime: event.timestamp,
        duration: event.duration,
      });
    }
    
    // 移除完成的线条
    if (event.type === SchedulerEventType.LINE_COMPLETE) {
      this.activeLines.delete(event.routeId);
    }
    
    // 发送事件
    this.emit(event);
  }

  /**
   * 更新活跃线条的进度
   */
  private updateLineProgress(): void {
    this.activeLines.forEach((lineInfo, routeId) => {
      const elapsed = this.currentTime - lineInfo.startTime;
      const progress = Math.max(0, Math.min(1, elapsed / lineInfo.duration));
      
      const progressEvent: LineProgressEvent = {
        id: `line-progress-${routeId}-${Date.now()}`,
        type: SchedulerEventType.LINE_PROGRESS,
        timestamp: this.currentTime,
        duration: 0,
        routeId,
        progress,
      };
      
      this.emit(progressEvent);
    });
  }

  /**
   * 在指定时间触发所有应该触发的事件
   */
  private triggerEventsAtTime(time: number): void {
    // 找到所有应该在这个时间点之前触发的事件
    const eventsToTrigger = this.events.filter(event => event.timestamp <= time);
    
    // 触发所有 LINE_START 事件
    eventsToTrigger
      .filter(event => event.type === SchedulerEventType.LINE_START)
      .forEach(event => {
        this.activeLines.set(event.routeId, {
          startTime: event.timestamp,
          duration: event.duration,
        });
        this.emit(event);
      });
    
    // 触发所有 RIPPLE_TRIGGER 事件
    eventsToTrigger
      .filter(event => event.type === SchedulerEventType.RIPPLE_TRIGGER)
      .forEach(event => this.emit(event));
  }

  /**
   * 查找指定时间点的事件索引
   */
  private findEventIndexAtTime(time: number): number {
    for (let i = 0; i < this.events.length; i++) {
      if (this.events[i].timestamp > time) {
        return i;
      }
    }
    return this.events.length;
  }

  /**
   * 处理播放完成
   */
  private handlePlaybackComplete(): void {
    this.setState(SchedulerState.COMPLETED);
    this.stopPlaybackLoop();
    this.activeLines.clear();
    
    this.emit({
      id: `scheduler-complete-${Date.now()}`,
      type: SchedulerEventType.SCHEDULER_COMPLETE,
      timestamp: this.totalDuration,
      duration: 0,
    });
    
    if (this.config.enableLogging) {
      console.info('播放完成');
    }
  }

  /**
   * 计算总时长
   */
  private calculateTotalDuration(): number {
    if (this.events.length === 0) return 0;
    
    const lastEvent = this.events[this.events.length - 1];
    return lastEvent.timestamp + lastEvent.duration;
  }

  /**
   * 设置状态
   */
  private setState(state: SchedulerState): void {
    this.state = state;
  }

  /**
   * 发送事件
   */
  private emit(event: SchedulerEvent): void {
    this.eventBus.next(event);
  }
}

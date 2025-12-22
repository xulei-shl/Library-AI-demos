/**
 * 叙事调度器类型定义
 * 参考：@docs/design/narrative_scheduler_20251215.md
 */

import { Route } from '../data/normalizers';

// 重新导出 Route 类型供外部使用
export type { Route };

/**
 * 事件类型枚举
 */
export enum SchedulerEventType {
  // 线条事件
  LINE_START = 'line:start',
  LINE_PROGRESS = 'line:progress',
  LINE_COMPLETE = 'line:complete',
  
  // 涟漪事件
  RIPPLE_TRIGGER = 'ripple:trigger',
  RIPPLE_COMPLETE = 'ripple:complete',
  
  // 播放控制事件
  PLAYBACK_PLAY = 'playback:play',
  PLAYBACK_PAUSE = 'playback:pause',
  PLAYBACK_SEEK = 'playback:seek',
  PLAYBACK_STOP = 'playback:stop',
  PLAYBACK_SPEED_CHANGE = 'playback:speed_change',
  
  // 调度器状态事件
  SCHEDULER_READY = 'scheduler:ready',
  SCHEDULER_COMPLETE = 'scheduler:complete',
  SCHEDULER_ERROR = 'scheduler:error',
}

/**
 * 基础调度事件接口
 */
export interface BaseSchedulerEvent {
  id: string;
  type: SchedulerEventType;
  timestamp: number; // 相对时间（毫秒）
  duration: number; // 事件持续时间（毫秒）
}

/**
 * 线条开始事件
 */
export interface LineStartEvent extends BaseSchedulerEvent {
  type: SchedulerEventType.LINE_START;
  routeId: string;
  route: Route;
  coordinates: [number, number][];
  color: string;
  year?: number;
}

/**
 * 线条进度事件
 */
export interface LineProgressEvent extends BaseSchedulerEvent {
  type: SchedulerEventType.LINE_PROGRESS;
  routeId: string;
  progress: number; // 0-1
}

/**
 * 线条完成事件
 */
export interface LineCompleteEvent extends BaseSchedulerEvent {
  type: SchedulerEventType.LINE_COMPLETE;
  routeId: string;
}

/**
 * 涟漪触发事件
 */
export interface RippleTriggerEvent extends BaseSchedulerEvent {
  type: SchedulerEventType.RIPPLE_TRIGGER;
  cityId: string;
  cityName: string;
  coordinates: [number, number];
  routeId: string;
  hasCollection: boolean;
  collectionMeta?: {
    title: string;
    date: string;
    location: string;
  };
  year?: number;
}

/**
 * 播放控制事件
 */
export interface PlaybackControlEvent extends BaseSchedulerEvent {
  type: SchedulerEventType.PLAYBACK_PLAY 
    | SchedulerEventType.PLAYBACK_PAUSE 
    | SchedulerEventType.PLAYBACK_SEEK 
    | SchedulerEventType.PLAYBACK_STOP
    | SchedulerEventType.PLAYBACK_SPEED_CHANGE;
  data?: {
    seekTime?: number;
    speed?: number;
  };
}

/**
 * 调度器状态事件
 */
export interface SchedulerStateEvent extends BaseSchedulerEvent {
  type: SchedulerEventType.SCHEDULER_READY 
    | SchedulerEventType.SCHEDULER_COMPLETE 
    | SchedulerEventType.SCHEDULER_ERROR;
  data?: {
    totalEvents?: number;
    totalDuration?: number;
    error?: string;
  };
}

/**
 * 联合事件类型
 */
export type SchedulerEvent = 
  | LineStartEvent 
  | LineProgressEvent 
  | LineCompleteEvent 
  | RippleTriggerEvent 
  | PlaybackControlEvent
  | SchedulerStateEvent;

/**
 * 时间轴配置
 */
export interface TimelineConfig {
  // 基础时长（毫秒）
  baseDuration: number;
  
  // 距离因子（每1000km增加的时长）
  distanceFactor: number;
  
  // 年份因子（用于调整不同年代的速度）
  yearFactor: number;
  
  // 涟漪延迟（线条完成后多久触发涟漪）
  rippleDelay: number;
  
  // 涟漪持续时间
  rippleDuration: number;
  
  // 最小间隔（两个事件之间的最小时间间隔）
  minInterval: number;
}

/**
 * 默认时间轴配置
 */
export const DEFAULT_TIMELINE_CONFIG: TimelineConfig = {
  baseDuration: 2000, // 2秒基础时长
  distanceFactor: 0.5, // 每1000km增加0.5秒
  yearFactor: 1.0, // 年份不影响速度
  rippleDelay: 200, // 线条完成后200ms触发涟漪
  rippleDuration: 600, // 涟漪持续600ms
  minInterval: 100, // 最小100ms间隔
};

/**
 * 调度器状态
 */
export enum SchedulerState {
  IDLE = 'idle',
  LOADING = 'loading',
  READY = 'ready',
  PLAYING = 'playing',
  PAUSED = 'paused',
  SEEKING = 'seeking',
  COMPLETED = 'completed',
  ERROR = 'error',
}

/**
 * 调度器配置
 */
export interface SchedulerConfig {
  timeline: TimelineConfig;
  enableLogging?: boolean;
  enablePerformanceMonitoring?: boolean;
}

/**
 * 默认调度器配置
 */
export const DEFAULT_SCHEDULER_CONFIG: SchedulerConfig = {
  timeline: DEFAULT_TIMELINE_CONFIG,
  enableLogging: true,
  enablePerformanceMonitoring: false,
};

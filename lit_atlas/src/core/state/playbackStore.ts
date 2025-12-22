import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { Subject } from 'rxjs';
import { Work, Route } from '../data/normalizers';

/**
 * 地图交互模式
 */
export enum MapInteractionMode {
  AUTO = 'auto',   // 自动播放模式，锁定用户输入
  MANUAL = 'manual' // 手动模式，允许用户交互
}

/**
 * 播放状态类型
 */
export interface PlaybackState {
  // 核心播放状态
  isPlaying: boolean;
  isPaused: boolean;
  isStopped: boolean;
  
  // 时间控制
  currentTime: number; // 当前播放时间（毫秒）
  duration: number; // 总时长（毫秒）
  playbackRate: number; // 播放速度（0.5x, 1x, 2x等）
  
  // 循环控制
  loopMode: 'none' | 'one' | 'all';
  currentLoopCount: number;
  maxLoopCount: number;
  
  // 事件控制
  currentEventIndex: number; // 当前播放的事件索引
  totalEvents: number; // 总事件数
  
  // 地图交互控制
  mapInteractionMode: MapInteractionMode; // 地图交互模式
  isMapInteractionLocked: boolean; // 地图交互是否被锁定
  
  // UI状态
  showControls: boolean;
  volume: number; // 音量（0-1）
}

/**
 * 播放操作类型
 */
export interface PlaybackActions {
  // 播放控制
  play: () => void;
  pause: () => void;
  stop: () => void;
  togglePlayPause: () => void;
  
  // 时间控制
  seek: (time: number) => void;
  setCurrentTime: (time: number) => void;
  setDuration: (duration: number) => void;
  
  // 速度控制
  setPlaybackRate: (rate: number) => void;
  
  // 循环控制
  setLoopMode: (mode: 'none' | 'one' | 'all') => void;
  resetLoop: () => void;
  
  // 事件控制
  setCurrentEventIndex: (index: number) => void;
  setTotalEvents: (count: number) => void;
  nextEvent: () => void;
  previousEvent: () => void;
  
  // 地图交互控制
  setMapInteractionMode: (mode: MapInteractionMode) => void;
  lockMapInteraction: () => void;
  unlockMapInteraction: () => void;
  toggleMapInteractionLock: () => void;
  
  // UI控制
  setShowControls: (show: boolean) => void;
  setVolume: (volume: number) => void;
  
  // 重置
  reset: () => void;
  resetToStart: () => void;
  
  // 工具方法
  getProgress: () => number; // 0-1之间的进度
  isAtEnd: () => boolean;
  isAtStart: () => boolean;
  getFormattedTime: (time?: number) => string;
}

/**
 * 播放事件类型定义
 */
export interface NarrativeEvent {
  id: string;
  type: 'route_start' | 'route_progress' | 'route_end' | 'ripple_trigger' | 'ink_line_start' | 'ink_line_progress';
  timestamp: number; // 相对时间（毫秒）
  duration: number; // 事件持续时间（毫秒）
  data: Record<string, unknown>; // 事件数据
}

/**
 * PlaybackStore类型
 */
export type PlaybackStore = PlaybackState & PlaybackActions;

/**
 * 创建全局播放事件总线
 */
export const playbackBus = new Subject<NarrativeEvent>();

/**
 * 预定义的播放速度选项
 */
export const PLAYBACK_SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 3];

/**
 * 默认播放速度
 */
export const DEFAULT_PLAYBACK_RATE = 1;

/**
 * PlaybackStore实现
 */
export const usePlaybackStore = create<PlaybackStore>()(
  subscribeWithSelector((set, get) => ({
    // 初始状态
    isPlaying: false,
    isPaused: false,
    isStopped: true,
    
    currentTime: 0,
    duration: 0,
    playbackRate: DEFAULT_PLAYBACK_RATE,
    
    loopMode: 'none',
    currentLoopCount: 0,
    maxLoopCount: 1,
    
    currentEventIndex: 0,
    totalEvents: 0,
    
    mapInteractionMode: MapInteractionMode.AUTO,
    isMapInteractionLocked: false,
    
    showControls: true,
    volume: 1,

    // 播放控制
    play: () => {
      const state = get();
      
      set({
        isPlaying: true,
        isPaused: false,
        isStopped: false,
        mapInteractionMode: MapInteractionMode.AUTO, // 播放时自动切换到 AUTO 模式
        isMapInteractionLocked: true // 锁定地图交互
      });
      
      // 广播播放事件
      playbackBus.next({
        id: `playback_${Date.now()}`,
        type: 'route_start',
        timestamp: state.currentTime,
        duration: 0,
        data: { action: 'play' }
      });
      
      console.info('开始播放，锁定地图交互');
    },

    pause: () => {
      set({
        isPlaying: false,
        isPaused: true,
        isStopped: false,
        isMapInteractionLocked: false // 暂停时解锁地图交互
      });
      
      // 广播暂停事件
      playbackBus.next({
        id: `playback_${Date.now()}`,
        type: 'route_end',
        timestamp: get().currentTime,
        duration: 0,
        data: { action: 'pause' }
      });
      
      console.info('暂停播放，解锁地图交互');
    },

    stop: () => {
      set({
        isPlaying: false,
        isPaused: false,
        isStopped: true,
        currentTime: 0,
        currentEventIndex: 0,
        mapInteractionMode: MapInteractionMode.AUTO,
        isMapInteractionLocked: false
      });
      
      // 广播停止事件
      playbackBus.next({
        id: `playback_${Date.now()}`,
        type: 'route_end',
        timestamp: 0,
        duration: 0,
        data: { action: 'stop' }
      });
      
      console.info('停止播放');
    },

    togglePlayPause: () => {
      const state = get();
      if (state.isPlaying) {
        get().pause();
      } else {
        get().play();
      }
    },

    // 时间控制
    seek: (time: number) => {
      const clampedTime = Math.max(0, Math.min(time, get().duration));
      
      set({ currentTime: clampedTime });
      
      // 广播跳转事件
      playbackBus.next({
        id: `seek_${Date.now()}`,
        type: 'route_progress',
        timestamp: clampedTime,
        duration: 0,
        data: { action: 'seek', time: clampedTime }
      });
      
      console.info(`跳转到时间: ${clampedTime}ms`);
    },

    setCurrentTime: (time: number) => {
      set({ currentTime: Math.max(0, time) });
    },

    setDuration: (duration: number) => {
      set({ duration: Math.max(0, duration) });
    },

    // 速度控制
    setPlaybackRate: (rate: number) => {
      const clampedRate = Math.max(0.1, Math.min(rate, 4));
      set({ playbackRate: clampedRate });
      
      console.info(`设置播放速度: ${clampedRate}x`);
    },

    // 循环控制
    setLoopMode: (mode: 'none' | 'one' | 'all') => {
      set({ 
        loopMode: mode,
        currentLoopCount: 0
      });
      
      console.info(`设置循环模式: ${mode}`);
    },

    resetLoop: () => {
      set({ 
        currentLoopCount: 0,
        currentTime: 0,
        currentEventIndex: 0
      });
    },

    // 事件控制
    setCurrentEventIndex: (index: number) => {
      const totalEvents = get().totalEvents;
      const clampedIndex = Math.max(0, Math.min(index, totalEvents - 1));
      set({ currentEventIndex: clampedIndex });
    },

    setTotalEvents: (count: number) => {
      set({ totalEvents: Math.max(0, count) });
    },

    nextEvent: () => {
      const state = get();
      if (state.currentEventIndex < state.totalEvents - 1) {
        set({ currentEventIndex: state.currentEventIndex + 1 });
      }
    },

    previousEvent: () => {
      const state = get();
      if (state.currentEventIndex > 0) {
        set({ currentEventIndex: state.currentEventIndex - 1 });
      }
    },

    // UI控制
    setShowControls: (show: boolean) => {
      set({ showControls: show });
    },

    setVolume: (volume: number) => {
      const clampedVolume = Math.max(0, Math.min(volume, 1));
      set({ volume: clampedVolume });
    },

    // 地图交互控制
    setMapInteractionMode: (mode: MapInteractionMode) => {
      set({ mapInteractionMode: mode });
      console.info(`设置地图交互模式: ${mode}`);
    },

    lockMapInteraction: () => {
      set({ 
        isMapInteractionLocked: true,
        mapInteractionMode: MapInteractionMode.AUTO
      });
      console.info('锁定地图交互');
    },

    unlockMapInteraction: () => {
      set({ 
        isMapInteractionLocked: false,
        mapInteractionMode: MapInteractionMode.MANUAL
      });
      console.info('解锁地图交互');
    },

    toggleMapInteractionLock: () => {
      const state = get();
      if (state.isMapInteractionLocked) {
        get().unlockMapInteraction();
      } else {
        get().lockMapInteraction();
      }
    },

    // 重置
    reset: () => {
      set({
        isPlaying: false,
        isPaused: false,
        isStopped: true,
        currentTime: 0,
        duration: 0,
        playbackRate: DEFAULT_PLAYBACK_RATE,
        loopMode: 'none',
        currentLoopCount: 0,
        currentEventIndex: 0,
        totalEvents: 0,
        volume: 1,
        mapInteractionMode: MapInteractionMode.AUTO,
        isMapInteractionLocked: false
      });
      
      console.info('重置播放状态');
    },

    resetToStart: () => {
      set({
        currentTime: 0,
        currentEventIndex: 0,
        isPlaying: false,
        isPaused: false,
        isStopped: true,
        mapInteractionMode: MapInteractionMode.AUTO,
        isMapInteractionLocked: false
      });
      
      // 广播重置事件
      playbackBus.next({
        id: `reset_${Date.now()}`,
        type: 'route_start',
        timestamp: 0,
        duration: 0,
        data: { action: 'reset_to_start' }
      });
      
      console.info('重置到开始位置');
    },

    // 工具方法
    getProgress: () => {
      const state = get();
      if (state.duration === 0) return 0;
      return Math.max(0, Math.min(1, state.currentTime / state.duration));
    },

    isAtEnd: () => {
      const state = get();
      return state.currentTime >= state.duration - 100; // 100ms 容差
    },

    isAtStart: () => {
      return get().currentTime <= 100; // 100ms 容差
    },

    getFormattedTime: (time?: number) => {
      const currentTime = time !== undefined ? time : get().currentTime;
      const seconds = Math.floor(currentTime / 1000);
      const minutes = Math.floor(seconds / 60);
      const hours = Math.floor(minutes / 60);
      
      const remainingMinutes = minutes % 60;
      const remainingSeconds = seconds % 60;
      
      if (hours > 0) {
        return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
      } else {
        return `${remainingMinutes}:${remainingSeconds.toString().padStart(2, '0')}`;
      }
    }
  }))
);

/**
 * 监听播放状态变化并触发相应的副作用
 */
usePlaybackStore.subscribe(
  (state) => state.isPlaying,
  (isPlaying, wasPlaying) => {
    if (isPlaying && !wasPlaying) {
      console.info('开始播放循环');
    } else if (!isPlaying && wasPlaying) {
      console.info('停止播放循环');
    }
  }
);

usePlaybackStore.subscribe(
  (state) => state.currentTime,
  (currentTime, previousTime) => {
    // 这里可以添加时间相关的副作用，如进度条更新等
    if (Math.abs(currentTime - previousTime) > 100) {
      // 时间变化超过100ms才记录，避免过于频繁
      console.debug(`播放时间更新: ${currentTime}ms`);
    }
  }
);
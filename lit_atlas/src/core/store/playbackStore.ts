/**
 * 播放控制状态管理 Store
 * 参考：@docs/design/playback_control_module_20251215.md
 */

import { create } from 'zustand';

/**
 * 播放状态
 */
export type PlaybackState = 'idle' | 'playing' | 'paused' | 'seeking';

/**
 * 播放速度
 */
export type PlaybackSpeed = 0.5 | 1 | 1.5 | 2;

/**
 * 播放控制状态
 */
interface PlaybackStoreState {
  // 播放状态
  state: PlaybackState;
  // 当前播放头位置（0-1）
  progress: number;
  // 播放速度
  speed: PlaybackSpeed;
  // 是否循环播放
  loop: boolean;
  // 当前年份（用于显示）
  currentYear: number | null;

  // Actions
  play: () => void;
  pause: () => void;
  seek: (progress: number) => void;
  reset: () => void;
  setSpeed: (speed: PlaybackSpeed) => void;
  setLoop: (loop: boolean) => void;
  setProgress: (progress: number) => void;
  setCurrentYear: (year: number | null) => void;
}

/**
 * 播放控制 Store
 */
export const usePlaybackStore = create<PlaybackStoreState>((set) => ({
  state: 'idle',
  progress: 0,
  speed: 1,
  loop: false,
  currentYear: null,

  play: () => set({ state: 'playing' }),

  pause: () => set({ state: 'paused' }),

  seek: (progress) =>
    set({
      state: 'seeking',
      progress: Math.max(0, Math.min(1, progress)),
    }),

  reset: () =>
    set({
      state: 'idle',
      progress: 0,
      currentYear: null,
    }),

  setSpeed: (speed) => set({ speed }),

  setLoop: (loop) => set({ loop }),

  setProgress: (progress) =>
    set({ progress: Math.max(0, Math.min(1, progress)) }),

  setCurrentYear: (year) => set({ currentYear: year }),
}));

/**
 * 播放控制模块类型定义
 * 参考：@docs/design/playback_control_module_20251215.md
 */

/**
 * 播放控制事件类型
 */
export enum PlaybackControlEvent {
  PLAY = 'PLAY',
  PAUSE = 'PAUSE',
  STOP = 'STOP',
  SEEK = 'SEEK',
  SPEED_CHANGE = 'SPEED_CHANGE',
  SKIP_FORWARD = 'SKIP_FORWARD',
  SKIP_BACKWARD = 'SKIP_BACKWARD',
}

/**
 * 播放速度选项
 */
export const PLAYBACK_SPEEDS = [0.5, 0.75, 1, 1.5, 2, 3, 4] as const;
export type PlaybackSpeed = (typeof PLAYBACK_SPEEDS)[number];

/**
 * 快捷键配置
 */
export interface HotkeyConfig {
  play: string; // Space
  skipForward: string; // ArrowRight
  skipBackward: string; // ArrowLeft
  speedUp: string; // Shift+ArrowRight
  speedDown: string; // Shift+ArrowLeft
}

/**
 * 默认快捷键配置
 */
export const DEFAULT_HOTKEYS: HotkeyConfig = {
  play: ' ',
  skipForward: 'ArrowRight',
  skipBackward: 'ArrowLeft',
  speedUp: 'Shift+ArrowRight',
  speedDown: 'Shift+ArrowLeft',
};

/**
 * Scrubber 配置
 */
export interface ScrubberConfig {
  throttleMs: number; // 节流间隔
  skipSeconds: number; // 跳转秒数
}

/**
 * 默认 Scrubber 配置
 */
export const DEFAULT_SCRUBBER_CONFIG: ScrubberConfig = {
  throttleMs: 16, // ~60fps
  skipSeconds: 5,
};

/**
 * 播放控制快捷键 Hook
 * 参考：@docs/design/playback_control_module_20251215.md
 */

import { useEffect, useCallback } from 'react';
import { HotkeyConfig, DEFAULT_HOTKEYS, PlaybackControlEvent } from './types';

/**
 * 快捷键回调函数类型
 */
export interface HotkeyCallbacks {
  onPlay: () => void;
  onSkipForward: () => void;
  onSkipBackward: () => void;
  onSpeedUp: () => void;
  onSpeedDown: () => void;
}

/**
 * 播放控制快捷键 Hook
 */
export function usePlaybackHotkeys(
  callbacks: HotkeyCallbacks,
  config: HotkeyConfig = DEFAULT_HOTKEYS,
  enabled: boolean = true
): void {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // 忽略在输入框中的按键
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      const key = event.key;
      const withShift = event.shiftKey;
      const withCtrl = event.ctrlKey || event.metaKey;

      // 避免与浏览器快捷键冲突
      if (withCtrl) {
        return;
      }

      // Space: Play/Pause
      if (key === config.play && !withShift) {
        event.preventDefault();
        callbacks.onPlay();
        return;
      }

      // ArrowRight: Skip Forward
      if (key === config.skipForward && !withShift) {
        event.preventDefault();
        callbacks.onSkipForward();
        return;
      }

      // ArrowLeft: Skip Backward
      if (key === config.skipBackward && !withShift) {
        event.preventDefault();
        callbacks.onSkipBackward();
        return;
      }

      // Shift+ArrowRight: Speed Up
      if (key === 'ArrowRight' && withShift) {
        event.preventDefault();
        callbacks.onSpeedUp();
        return;
      }

      // Shift+ArrowLeft: Speed Down
      if (key === 'ArrowLeft' && withShift) {
        event.preventDefault();
        callbacks.onSpeedDown();
        return;
      }
    },
    [callbacks, config]
  );

  useEffect(() => {
    if (!enabled) {
      return;
    }

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [enabled, handleKeyDown]);
}

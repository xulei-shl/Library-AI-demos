/**
 * Overlay 播放控制 Hook
 * 处理联动/独立进度条逻辑
 * 参考：@docs/design/overlay_mode_module_20251215.md
 */

import { useState, useEffect, useCallback } from 'react';
import { NarrativeScheduler } from '../scheduler/narrativeScheduler';
import { OverlayMode } from './types';
import { useOverlayStore } from './OverlayController';

/**
 * Overlay 播放状态
 */
export interface OverlayPlaybackState {
  primaryProgress: number;
  secondaryProgress: number;
  isLinked: boolean;
}

/**
 * Overlay 播放控制 Hook
 */
export function useOverlayPlayback(
  primaryScheduler: NarrativeScheduler,
  secondaryScheduler: NarrativeScheduler | null
): OverlayPlaybackState {
  const mode = useOverlayStore((state) => state.mode);
  const [primaryProgress, setPrimaryProgress] = useState(0);
  const [secondaryProgress, setSecondaryProgress] = useState(0);

  const isLinked = mode === OverlayMode.LINKED;

  // 监听主调度器
  useEffect(() => {
    const subscription = primaryScheduler.on(() => {
      const progress = primaryScheduler.getProgress();
      setPrimaryProgress(progress);

      // 联动模式下同步副调度器
      if (isLinked && secondaryScheduler) {
        const time = progress * secondaryScheduler.getTotalDuration();
        secondaryScheduler.seek(time);
      }
    });

    return () => subscription.unsubscribe();
  }, [primaryScheduler, secondaryScheduler, isLinked]);

  // 监听副调度器（独立模式）
  useEffect(() => {
    if (!secondaryScheduler || isLinked) {
      return;
    }

    const subscription = secondaryScheduler.on(() => {
      setSecondaryProgress(secondaryScheduler.getProgress());
    });

    return () => subscription.unsubscribe();
  }, [secondaryScheduler, isLinked]);

  return {
    primaryProgress,
    secondaryProgress,
    isLinked,
  };
}

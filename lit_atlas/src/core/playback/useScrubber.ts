/**
 * 播放进度条拖拽 Hook
 * 参考：@docs/design/playback_control_module_20251215.md
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { ScrubberConfig, DEFAULT_SCRUBBER_CONFIG } from './types';

/**
 * Scrubber 状态
 */
export interface ScrubberState {
  isDragging: boolean;
  progress: number; // 0-1
  displayProgress: number; // 拖拽时的临时进度
}

/**
 * Scrubber 回调函数
 */
export interface ScrubberCallbacks {
  onSeekStart: () => void;
  onSeek: (progress: number) => void;
  onSeekEnd: (progress: number) => void;
}

/**
 * Scrubber Hook 返回值
 */
export interface UseScrubberReturn {
  state: ScrubberState;
  handlers: {
    onMouseDown: (event: React.MouseEvent<HTMLElement>) => void;
    onTouchStart: (event: React.TouchEvent<HTMLElement>) => void;
  };
  setProgress: (progress: number) => void;
}

/**
 * 播放进度条拖拽 Hook
 */
export function useScrubber(
  callbacks: ScrubberCallbacks,
  config: ScrubberConfig = DEFAULT_SCRUBBER_CONFIG
): UseScrubberReturn {
  const [state, setState] = useState<ScrubberState>({
    isDragging: false,
    progress: 0,
    displayProgress: 0,
  });

  const containerRef = useRef<HTMLElement | null>(null);
  const lastSeekTimeRef = useRef<number>(0);
  const rafIdRef = useRef<number | null>(null);

  // 节流 Seek 事件
  const throttledSeek = useCallback(
    (progress: number) => {
      const now = Date.now();
      if (now - lastSeekTimeRef.current >= config.throttleMs) {
        callbacks.onSeek(progress);
        lastSeekTimeRef.current = now;
      }
    },
    [callbacks, config.throttleMs]
  );

  // 计算进度
  const calculateProgress = useCallback((clientX: number, container: HTMLElement): number => {
    const rect = container.getBoundingClientRect();
    const x = clientX - rect.left;
    const progress = Math.max(0, Math.min(1, x / rect.width));
    return progress;
  }, []);

  // 鼠标/触摸移动处理
  const handleMove = useCallback(
    (clientX: number) => {
      if (!containerRef.current) return;

      const progress = calculateProgress(clientX, containerRef.current);
      setState((prev) => ({ ...prev, displayProgress: progress }));
      throttledSeek(progress);
    },
    [calculateProgress, throttledSeek]
  );

  // 鼠标/触摸结束处理
  const handleEnd = useCallback(() => {
    if (!state.isDragging) return;

    setState((prev) => ({
      ...prev,
      isDragging: false,
      progress: prev.displayProgress,
    }));

    callbacks.onSeekEnd(state.displayProgress);

    // 清理事件监听
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
  }, [state.isDragging, state.displayProgress, callbacks]);

  // 鼠标按下
  const onMouseDown = useCallback(
    (event: React.MouseEvent<HTMLElement>) => {
      event.preventDefault();
      containerRef.current = event.currentTarget;

      const progress = calculateProgress(event.clientX, event.currentTarget);
      setState({
        isDragging: true,
        progress: state.progress,
        displayProgress: progress,
      });

      callbacks.onSeekStart();
      throttledSeek(progress);
    },
    [calculateProgress, callbacks, throttledSeek, state.progress]
  );

  // 触摸开始
  const onTouchStart = useCallback(
    (event: React.TouchEvent<HTMLElement>) => {
      event.preventDefault();
      containerRef.current = event.currentTarget;

      const touch = event.touches[0];
      const progress = calculateProgress(touch.clientX, event.currentTarget);
      setState({
        isDragging: true,
        progress: state.progress,
        displayProgress: progress,
      });

      callbacks.onSeekStart();
      throttledSeek(progress);
    },
    [calculateProgress, callbacks, throttledSeek, state.progress]
  );

  // 全局鼠标移动监听
  useEffect(() => {
    if (!state.isDragging) return;

    const handleMouseMove = (event: MouseEvent) => {
      event.preventDefault();
      rafIdRef.current = requestAnimationFrame(() => {
        handleMove(event.clientX);
      });
    };

    const handleTouchMove = (event: TouchEvent) => {
      event.preventDefault();
      const touch = event.touches[0];
      rafIdRef.current = requestAnimationFrame(() => {
        handleMove(touch.clientX);
      });
    };

    const handleMouseUp = () => {
      handleEnd();
    };

    const handleTouchEnd = () => {
      handleEnd();
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchmove', handleTouchMove, { passive: false });
    window.addEventListener('touchend', handleTouchEnd);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchmove', handleTouchMove);
      window.removeEventListener('touchend', handleTouchEnd);

      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, [state.isDragging, handleMove, handleEnd]);

  // 外部更新进度
  const setProgress = useCallback((progress: number) => {
    setState((prev) => ({
      ...prev,
      progress: Math.max(0, Math.min(1, progress)),
      displayProgress: prev.isDragging ? prev.displayProgress : Math.max(0, Math.min(1, progress)),
    }));
  }, []);

  return {
    state,
    handlers: {
      onMouseDown,
      onTouchStart,
    },
    setProgress,
  };
}

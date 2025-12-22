/**
 * 播放控制栏主组件
 * 参考：@docs/design/playback_control_module_20251215.md
 */

'use client';

import React, { useEffect, useCallback, useMemo } from 'react';
import { NarrativeScheduler } from '../scheduler/narrativeScheduler';
import { SchedulerState, SchedulerEventType } from '../scheduler/types';
import { useScrubber } from './useScrubber';
import { usePlaybackHotkeys } from './usePlaybackHotkeys';
import { SpeedMenu } from './SpeedMenu';
import { PlaybackSpeed, PLAYBACK_SPEEDS, DEFAULT_SCRUBBER_CONFIG } from './types';
import { SPACING, THEME_COLORS, TYPOGRAPHY, DURATIONS, EASING } from '../theme';
import { usePlaybackStore } from '../state/playbackStore';

// 简化常量引用
const COLORS = {
  surface: { paper: THEME_COLORS.paper.light },
  text: { primary: THEME_COLORS.ink.primary, secondary: '#666' },
  border: { default: '#ddd' },
  primary: { main: THEME_COLORS.interactive.focus },
};

const ANIMATIONS = {
  duration: { fast: `${DURATIONS.fast}ms` },
  easing: { standard: EASING.ui },
};

export interface PlaybackControlProps {
  scheduler: NarrativeScheduler;
  className?: string;
  style?: React.CSSProperties;
  enableHotkeys?: boolean;
  showYear?: boolean;
}

export function PlaybackControl({
  scheduler,
  className,
  style,
  enableHotkeys = true,
  showYear = true,
}: PlaybackControlProps) {
  const [schedulerState, setSchedulerState] = React.useState<SchedulerState>(scheduler.getState());
  const [currentYear, setCurrentYear] = React.useState<number | null>(null);
  const [speed, setSpeed] = React.useState<PlaybackSpeed>(1);

  // 从 playbackStore 获取地图交互状态
  const mapInteractionMode = usePlaybackStore((state) => state.mapInteractionMode);
  const isMapInteractionLocked = usePlaybackStore((state) => state.isMapInteractionLocked);
  const toggleMapInteractionLock = usePlaybackStore((state) => state.toggleMapInteractionLock);

  const isPlaying = schedulerState === SchedulerState.PLAYING;

  const scrubberCallbacks = useMemo(
    () => ({
      onSeekStart: () => {
        if (isPlaying) scheduler.pause();
      },
      onSeek: (progress: number) => {
        scheduler.seek(progress * scheduler.getTotalDuration());
      },
      onSeekEnd: (progress: number) => {
        scheduler.seek(progress * scheduler.getTotalDuration());
      },
    }),
    [scheduler, isPlaying]
  );

  const { state: scrubberState, handlers: scrubberHandlers, setProgress } = useScrubber(
    scrubberCallbacks,
    DEFAULT_SCRUBBER_CONFIG
  );

  const handlePlayPause = useCallback(() => {
    isPlaying ? scheduler.pause() : scheduler.play();
  }, [scheduler, isPlaying]);

  const handleSkip = useCallback(
    (seconds: number) => {
      const newTime = Math.max(0, Math.min(scheduler.getTotalDuration(), scheduler.getCurrentTime() + seconds * 1000));
      scheduler.seek(newTime);
    },
    [scheduler]
  );

  const handleSpeedChange = useCallback(
    (newSpeed: PlaybackSpeed) => {
      setSpeed(newSpeed);
      scheduler.setSpeed(newSpeed);
      try {
        localStorage.setItem('playback-speed', String(newSpeed));
      } catch (e) {
        console.warn('无法保存播放速度', e);
      }
    },
    [scheduler]
  );

  const handleSpeedUp = useCallback(() => {
    const idx = PLAYBACK_SPEEDS.indexOf(speed);
    if (idx < PLAYBACK_SPEEDS.length - 1) handleSpeedChange(PLAYBACK_SPEEDS[idx + 1]);
  }, [speed, handleSpeedChange]);

  const handleSpeedDown = useCallback(() => {
    const idx = PLAYBACK_SPEEDS.indexOf(speed);
    if (idx > 0) handleSpeedChange(PLAYBACK_SPEEDS[idx - 1]);
  }, [speed, handleSpeedChange]);

  usePlaybackHotkeys(
    {
      onPlay: handlePlayPause,
      onSkipForward: () => handleSkip(5),
      onSkipBackward: () => handleSkip(-5),
      onSpeedUp: handleSpeedUp,
      onSpeedDown: handleSpeedDown,
    },
    undefined,
    enableHotkeys
  );

  useEffect(() => {
    const sub = scheduler.on((event) => {
      setSchedulerState(scheduler.getState());
      if (!scrubberState.isDragging) setProgress(scheduler.getProgress());
      if (event.type === SchedulerEventType.RIPPLE_TRIGGER && event.year) {
        setCurrentYear(event.year);
      }
    });

    try {
      const saved = localStorage.getItem('playback-speed');
      if (saved) {
        const parsed = parseFloat(saved) as PlaybackSpeed;
        if (PLAYBACK_SPEEDS.includes(parsed)) {
          setSpeed(parsed);
          scheduler.setSpeed(parsed);
        }
      }
    } catch (e) {}

    return () => sub.unsubscribe();
  }, [scheduler, scrubberState.isDragging, setProgress]);

  const formatTime = (ms: number) => {
    const s = Math.floor(ms / 1000);
    return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;
  };

  const displayProgress = scrubberState.isDragging ? scrubberState.displayProgress : scrubberState.progress;

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: SPACING.md,
        padding: SPACING.lg,
        background: COLORS.surface.paper,
        borderRadius: SPACING.sm,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        ...style,
      }}
      role="region"
      aria-label="播放控制"
    >
      {showYear && currentYear && (
        <div
          style={{
            fontSize: TYPOGRAPHY.fontSize['2xl'],
            fontWeight: TYPOGRAPHY.fontWeight.bold,
            color: COLORS.text.primary,
            textAlign: 'center',
            fontFamily: TYPOGRAPHY.fontFamily.mono,
          }}
          aria-live="polite"
        >
          {currentYear}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: SPACING.sm }}>
        <span style={{ fontSize: TYPOGRAPHY.fontSize.xs, color: COLORS.text.secondary, fontFamily: TYPOGRAPHY.fontFamily.mono, minWidth: '40px' }}>
          {formatTime(scheduler.getCurrentTime())}
        </span>

        <div
          {...scrubberHandlers}
          role="slider"
          aria-label="播放进度"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(displayProgress * 100)}
          tabIndex={0}
          style={{
            flex: 1,
            height: '32px',
            position: 'relative',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <div style={{ width: '100%', height: '4px', background: COLORS.border.default, borderRadius: '2px', position: 'relative' }}>
            <div
              style={{
                position: 'absolute',
                left: 0,
                top: 0,
                height: '100%',
                width: `${displayProgress * 100}%`,
                background: COLORS.primary.main,
                borderRadius: '2px',
                transition: scrubberState.isDragging ? 'none' : `width ${ANIMATIONS.duration.fast} linear`,
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: `${displayProgress * 100}%`,
                top: '50%',
                transform: 'translate(-50%, -50%)',
                width: '16px',
                height: '16px',
                background: COLORS.primary.main,
                borderRadius: '50%',
                border: `2px solid ${COLORS.surface.paper}`,
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                transition: scrubberState.isDragging ? 'none' : `left ${ANIMATIONS.duration.fast} linear`,
              }}
            />
          </div>
        </div>

        <span style={{ fontSize: TYPOGRAPHY.fontSize.xs, color: COLORS.text.secondary, fontFamily: TYPOGRAPHY.fontFamily.mono, minWidth: '40px' }}>
          {formatTime(scheduler.getTotalDuration())}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: SPACING.md }}>
        <button
          onClick={() => handleSkip(-5)}
          aria-label="后退 5 秒"
          style={{
            padding: SPACING.sm,
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: COLORS.text.primary,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M11 18V6L5 12L11 18Z" fill="currentColor" />
            <path d="M18 18V6L12 12L18 18Z" fill="currentColor" />
          </svg>
        </button>

        <button
          onClick={handlePlayPause}
          aria-label={isPlaying ? '暂停' : '播放'}
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            background: COLORS.primary.main,
            border: 'none',
            cursor: 'pointer',
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: `transform ${ANIMATIONS.duration.fast} ${ANIMATIONS.easing.standard}`,
          }}
          onMouseEnter={(e) => (e.currentTarget.style.transform = 'scale(1.05)')}
          onMouseLeave={(e) => (e.currentTarget.style.transform = 'scale(1)')}
        >
          {isPlaying ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <rect x="6" y="4" width="4" height="16" fill="currentColor" />
              <rect x="14" y="4" width="4" height="16" fill="currentColor" />
            </svg>
          ) : (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M8 5V19L19 12L8 5Z" fill="currentColor" />
            </svg>
          )}
        </button>

        <button
          onClick={() => handleSkip(5)}
          aria-label="前进 5 秒"
          style={{
            padding: SPACING.sm,
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: COLORS.text.primary,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M13 6V18L19 12L13 6Z" fill="currentColor" />
            <path d="M6 6V18L12 12L6 6Z" fill="currentColor" />
          </svg>
        </button>

        <SpeedMenu currentSpeed={speed} onSpeedChange={handleSpeedChange} />

        {/* 地图交互锁定状态指示器 */}
        <button
          onClick={toggleMapInteractionLock}
          aria-label={isMapInteractionLocked ? '解锁地图交互' : '锁定地图交互'}
          title={isMapInteractionLocked ? '点击解锁地图交互' : '点击锁定地图交互'}
          style={{
            padding: SPACING.sm,
            background: isMapInteractionLocked ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)',
            border: `1px solid ${isMapInteractionLocked ? '#ef4444' : '#22c55e'}`,
            borderRadius: SPACING.xs,
            cursor: 'pointer',
            color: isMapInteractionLocked ? '#ef4444' : '#22c55e',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: `all ${ANIMATIONS.duration.fast} ${ANIMATIONS.easing.standard}`,
            fontSize: TYPOGRAPHY.fontSize.sm,
            fontWeight: TYPOGRAPHY.fontWeight.medium,
            gap: SPACING.xs,
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = isMapInteractionLocked ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = isMapInteractionLocked ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 197, 94, 0.1)';
          }}
        >
          <span>{isMapInteractionLocked ? '🔒' : '🔓'}</span>
          <span style={{ fontSize: TYPOGRAPHY.fontSize.xs }}>
            {isMapInteractionLocked ? '地图已锁定' : '地图可交互'}
          </span>
        </button>
      </div>
    </div>
  );
}

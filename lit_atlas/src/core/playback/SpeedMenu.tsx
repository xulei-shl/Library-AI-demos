/**
 * 播放速度选择菜单
 * 参考：@docs/design/playback_control_module_20251215.md
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import { PLAYBACK_SPEEDS, PlaybackSpeed } from './types';
import { SPACING, THEME_COLORS, TYPOGRAPHY, DURATIONS, EASING } from '../theme';

/**
 * SpeedMenu Props
 */
export interface SpeedMenuProps {
  currentSpeed: PlaybackSpeed;
  onSpeedChange: (speed: PlaybackSpeed) => void;
  disabled?: boolean;
}

/**
 * 播放速度选择菜单组件
 */
export function SpeedMenu({ currentSpeed, onSpeedChange, disabled = false }: SpeedMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭菜单
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleSpeedSelect = (speed: PlaybackSpeed) => {
    onSpeedChange(speed);
    setIsOpen(false);
  };

  return (
    <div ref={menuRef} style={{ position: 'relative' }}>
      {/* 速度按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        aria-label={`播放速度: ${currentSpeed}x`}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        style={{
          padding: `${SPACING.xs} ${SPACING.sm}`,
          background: THEME_COLORS.paper.light,
          border: `1px solid ${THEME_COLORS.interactive.disabled}`,
          borderRadius: SPACING.xs,
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          fontSize: TYPOGRAPHY.fontSize.sm,
          fontWeight: TYPOGRAPHY.fontWeight.medium,
          color: THEME_COLORS.ink.primary,
          transition: `all ${DURATIONS.fast}ms ${EASING.ui}`,
          display: 'flex',
          alignItems: 'center',
          gap: SPACING.xs,
        }}
        onMouseEnter={(e) => {
          if (!disabled) {
            e.currentTarget.style.background = THEME_COLORS.interactive.hover;
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = THEME_COLORS.paper.light;
        }}
      >
        <span>{currentSpeed}x</span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 12 12"
          fill="none"
          style={{
            transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: `transform ${DURATIONS.fast}ms ${EASING.ui}`,
          }}
        >
          <path
            d="M2 4L6 8L10 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div
          role="menu"
          aria-label="播放速度选项"
          style={{
            position: 'absolute',
            bottom: '100%',
            left: 0,
            marginBottom: SPACING.xs,
            background: THEME_COLORS.paper.light,
            border: `1px solid ${THEME_COLORS.interactive.disabled}`,
            borderRadius: SPACING.xs,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            minWidth: '80px',
            zIndex: 1000,
            animation: `fadeIn ${DURATIONS.fast}ms ${EASING.ui}`,
          }}
        >
          {PLAYBACK_SPEEDS.map((speed) => (
            <button
              key={speed}
              role="menuitem"
              onClick={() => handleSpeedSelect(speed)}
              aria-label={`设置速度为 ${speed}x`}
              style={{
                width: '100%',
                padding: `${SPACING.xs} ${SPACING.sm}`,
                background: speed === currentSpeed ? THEME_COLORS.interactive.hover : 'transparent',
                border: 'none',
                cursor: 'pointer',
                fontSize: TYPOGRAPHY.fontSize.sm,
                fontWeight: speed === currentSpeed ? TYPOGRAPHY.fontWeight.medium : TYPOGRAPHY.fontWeight.normal,
                color: speed === currentSpeed ? THEME_COLORS.ink.accent : THEME_COLORS.ink.primary,
                textAlign: 'left',
                transition: `all ${DURATIONS.fast}ms ${EASING.ui}`,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = THEME_COLORS.interactive.hover;
              }}
              onMouseLeave={(e) => {
                if (speed !== currentSpeed) {
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              {speed}x
            </button>
          ))}
        </div>
      )}

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}


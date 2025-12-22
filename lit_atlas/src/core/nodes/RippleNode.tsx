/**
 * 涟漪节点组件
 * 呈现城市节点的冲击、定格与呼吸动画
 * 参考：@docs/design/ripple_node_component_20251215.md
 */

import React, { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRippleState, RippleState } from './useRippleState';
import { NodeTooltip } from './nodeTooltip';

/**
 * RippleNode组件属性
 */
export interface RippleNodeProps {
  cityId: string;
  cityName: string;
  coordinates: [number, number]; // 屏幕坐标
  hasCollection: boolean;
  collectionMeta?: {
    title: string;
    date: string;
    location: string;
  };
  year?: number;
  color?: string;
  onTrigger?: () => void;
  onClick?: (cityId: string) => void;
  className?: string;
  // Overlay 模式支持
  overlayMode?: boolean;
  secondaryYear?: number;
  secondaryColor?: string;
  mixedColor?: string;
  overlayStroke?: string | null;
}

/**
 * RippleNode组件
 */
export const RippleNode = React.memo<RippleNodeProps>(({
  cityId,
  cityName,
  coordinates,
  hasCollection,
  collectionMeta,
  year,
  color = '#2c3e50',
  onTrigger,
  onClick,
  className = '',
  overlayMode = false,
  secondaryYear,
  secondaryColor,
  mixedColor,
  overlayStroke,
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<'top' | 'bottom' | 'left' | 'right'>('top');
  
  // 使用状态机Hook
  const { state, trigger, reset } = useRippleState({
    hasCollection,
    onRippleComplete: onTrigger,
  });

  // 确定节点颜色（Overlay 模式下使用混合色）
  const nodeColor = overlayMode && mixedColor ? mixedColor : color;

  // 处理点击
  const handleClick = useCallback(() => {
    onClick?.(cityId);
  }, [cityId, onClick]);

  // 处理鼠标悬停
  const handleMouseEnter = useCallback(() => {
    if (state === RippleState.STATIC || state === RippleState.BREATHING) {
      setShowTooltip(true);
    }
  }, [state]);

  const handleMouseLeave = useCallback(() => {
    setShowTooltip(false);
  }, []);

  // 处理键盘事件（无障碍）
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }, [handleClick]);

  // 根据节点位置调整Tooltip方向
  useEffect(() => {
    const [x, y] = coordinates;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    
    // 简单的边界检测
    if (x < viewportWidth * 0.25) {
      setTooltipPosition('right');
    } else if (x > viewportWidth * 0.75) {
      setTooltipPosition('left');
    } else if (y < viewportHeight * 0.25) {
      setTooltipPosition('bottom');
    } else {
      setTooltipPosition('top');
    }
  }, [coordinates]);

  // 渲染不同状态的节点
  const renderNode = () => {
    const [x, y] = coordinates;
    
    switch (state) {
      case RippleState.HIDDEN:
        return null;
      
      case RippleState.RIPPLING:
        return (
          <g transform={`translate(${x}, ${y})`}>
            {/* 冲击波动画 */}
            <motion.circle
              cx={0}
              cy={0}
              r={0}
              fill="none"
              stroke={nodeColor}
              strokeWidth={2}
              initial={{ r: 0, opacity: 1 }}
              animate={{ r: 20, opacity: 0 }}
              transition={{ duration: 0.6, ease: 'easeOut' }}
            />
            <motion.circle
              cx={0}
              cy={0}
              r={0}
              fill="none"
              stroke={nodeColor}
              strokeWidth={1.5}
              initial={{ r: 0, opacity: 0.8 }}
              animate={{ r: 30, opacity: 0 }}
              transition={{ duration: 0.8, ease: 'easeOut', delay: 0.1 }}
            />
            {/* 描边（低对比度时） */}
            {overlayStroke && (
              <motion.circle
                cx={0}
                cy={0}
                r={3}
                fill={overlayStroke}
                initial={{ scale: 0 }}
                animate={{ scale: 1.2 }}
                transition={{ duration: 0.3, ease: 'backOut' }}
              />
            )}
            {/* 中心点 */}
            <motion.circle
              cx={0}
              cy={0}
              r={3}
              fill={nodeColor}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ duration: 0.3, ease: 'backOut' }}
            />
          </g>
        );
      
      case RippleState.STATIC:
        return (
          <g
            transform={`translate(${x}, ${y})`}
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            onKeyDown={handleKeyDown}
            role="button"
            tabIndex={0}
            aria-label={`城市节点: ${cityName}${year ? `, ${year}年` : ''}${overlayMode && secondaryYear ? ` / ${secondaryYear}年` : ''}`}
            className="cursor-pointer focus:outline-none"
          >
            {/* 描边（低对比度时） */}
            {overlayStroke && (
              <circle
                cx={0}
                cy={0}
                r={5}
                fill={overlayStroke}
                opacity={0.9}
              />
            )}
            {/* 实心墨点 */}
            <circle
              cx={0}
              cy={0}
              r={4}
              fill={nodeColor}
              opacity={0.9}
              style={{ filter: 'url(#ink-blur)' }}
            />
            {/* 外圈（悬停效果） */}
            <motion.circle
              cx={0}
              cy={0}
              r={6}
              fill="none"
              stroke={nodeColor}
              strokeWidth={1}
              opacity={0}
              whileHover={{ opacity: 0.5, r: 8 }}
              transition={{ duration: 0.2 }}
            />
          </g>
        );
      
      case RippleState.BREATHING:
        return (
          <g
            transform={`translate(${x}, ${y})`}
            onClick={handleClick}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            onKeyDown={handleKeyDown}
            role="button"
            tabIndex={0}
            aria-label={`城市节点: ${cityName}${year ? `, ${year}年` : ''}${overlayMode && secondaryYear ? ` / ${secondaryYear}年` : ''}, 有馆藏`}
            className="cursor-pointer focus:outline-none"
          >
            {/* 呼吸发光效果 */}
            <motion.circle
              cx={0}
              cy={0}
              r={8}
              fill={nodeColor}
              opacity={0.2}
              animate={{
                r: [8, 12, 8],
                opacity: [0.2, 0.4, 0.2],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
              style={{ filter: 'blur(3px)' }}
            />
            {/* 描边（低对比度时） */}
            {overlayStroke && (
              <circle
                cx={0}
                cy={0}
                r={6}
                fill={overlayStroke}
                opacity={0.95}
              />
            )}
            {/* 实心墨点 */}
            <circle
              cx={0}
              cy={0}
              r={5}
              fill={nodeColor}
              opacity={0.95}
              style={{ filter: 'url(#ink-blur)' }}
            />
            {/* 馆藏标记 */}
            <circle
              cx={0}
              cy={0}
              r={2}
              fill="white"
              opacity={0.8}
            />
          </g>
        );
      
      default:
        return null;
    }
  };

  return (
    <>
      <g className={`ripple-node ${className}`} data-city-id={cityId}>
        {renderNode()}
      </g>
      
      {/* Tooltip */}
      <AnimatePresence>
        {showTooltip && (state === RippleState.STATIC || state === RippleState.BREATHING) && (
          <NodeTooltip
            cityName={cityName}
            year={year}
            hasCollection={hasCollection}
            collectionMeta={collectionMeta}
            position={tooltipPosition}
            coordinates={coordinates}
            overlayMode={overlayMode}
            secondaryYear={secondaryYear}
            secondaryColor={secondaryColor}
          />
        )}
      </AnimatePresence>
    </>
  );
});

RippleNode.displayName = 'RippleNode';

/**
 * 触发涟漪效果的辅助函数
 */
export function triggerRipple(nodeRef: React.RefObject<any>): void {
  if (nodeRef.current && typeof nodeRef.current.trigger === 'function') {
    nodeRef.current.trigger();
  }
}

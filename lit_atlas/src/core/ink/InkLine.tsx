/**
 * 墨迹线条组件
 * 渲染具有方向渐变和生长动画的SVG曲线
 * 参考：@docs/design/ink_line_component_20251215.md
 */

import React, { useEffect, useRef, useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useInkAnimation } from './useInkAnimation';
import { createCurvePath } from './curveFactory';
import { createGradientId, InkGradient } from './gradients';

/**
 * InkLine组件属性
 */
export interface InkLineProps {
  routeId: string;
  coordinates: [number, number][];
  progress: number; // 0-1
  color: string;
  duration: number;
  delay?: number;
  strokeWidth?: number;
  opacity?: number;
  onComplete?: (routeId: string) => void;
  className?: string;
}

/**
 * InkLine组件
 */
export const InkLine = React.memo<InkLineProps>(({
  routeId,
  coordinates,
  progress,
  color,
  duration,
  delay = 0,
  strokeWidth = 2,
  opacity = 0.8,
  onComplete,
  className = '',
}) => {
  const pathRef = useRef<SVGPathElement>(null);
  const [pathLength, setPathLength] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  // 生成曲线路径
  const pathData = useMemo(() => {
    return createCurvePath(coordinates);
  }, [coordinates]);

  // 生成渐变ID
  const gradientId = useMemo(() => {
    return createGradientId(routeId);
  }, [routeId]);

  // 计算路径长度
  useEffect(() => {
    if (pathRef.current) {
      const length = pathRef.current.getTotalLength();
      setPathLength(length);
    }
  }, [pathData]);

  // 使用动画Hook
  const { dashOffset, animatedProgress } = useInkAnimation({
    progress,
    pathLength,
    duration,
    delay,
  });

  // 检测完成状态
  useEffect(() => {
    if (animatedProgress >= 0.99 && !isComplete) {
      setIsComplete(true);
      onComplete?.(routeId);
    }
  }, [animatedProgress, isComplete, routeId, onComplete]);

  // 如果没有有效路径，不渲染
  if (!pathData || coordinates.length < 2) {
    return null;
  }

  return (
    <g className={`ink-line ${className}`} data-route-id={routeId}>
      {/* 渐变定义 */}
      <InkGradient id={gradientId} color={color} />
      
      {/* 背景线（可选，用于增强视觉效果） */}
      <motion.path
        d={pathData}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth + 1}
        strokeOpacity={opacity * 0.3}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: animatedProgress }}
        transition={{ duration: 0.1, ease: 'linear' }}
      />
      
      {/* 主线条 */}
      <path
        ref={pathRef}
        d={pathData}
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth={strokeWidth}
        strokeOpacity={opacity}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={pathLength}
        strokeDashoffset={dashOffset}
        style={{
          filter: 'url(#ink-blur)',
          transition: 'stroke-dashoffset 0.05s linear',
        }}
      />
      
      {/* 发光效果（完成时） */}
      {isComplete && (
        <motion.path
          d={pathData}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth * 1.5}
          strokeOpacity={0}
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ strokeOpacity: 0.6 }}
          animate={{ strokeOpacity: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          style={{ filter: 'blur(4px)' }}
        />
      )}
    </g>
  );
});

InkLine.displayName = 'InkLine';

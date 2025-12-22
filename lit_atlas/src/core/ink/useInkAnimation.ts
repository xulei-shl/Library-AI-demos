/**
 * 墨迹动画Hook
 * 管理线条生长动画的状态和计算
 * 参考：@docs/design/ink_line_component_20251215.md
 */

import { useState, useEffect, useRef } from 'react';

/**
 * 动画配置
 */
export interface InkAnimationConfig {
  progress: number; // 外部传入的进度（0-1）
  pathLength: number; // 路径总长度
  duration: number; // 动画持续时间
  delay?: number; // 延迟时间
  easing?: (t: number) => number; // 缓动函数
}

/**
 * 动画返回值
 */
export interface InkAnimationResult {
  dashOffset: number; // stroke-dashoffset值
  animatedProgress: number; // 动画进度（0-1）
  isAnimating: boolean; // 是否正在动画
}

/**
 * 默认缓动函数（ease-out）
 */
const defaultEasing = (t: number): number => {
  return 1 - Math.pow(1 - t, 3);
};

/**
 * 墨迹动画Hook
 */
export function useInkAnimation({
  progress,
  pathLength,
  duration,
  delay = 0,
  easing = defaultEasing,
}: InkAnimationConfig): InkAnimationResult {
  const [dashOffset, setDashOffset] = useState(pathLength);
  const [animatedProgress, setAnimatedProgress] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  
  const animationFrameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number | null>(null);

  useEffect(() => {
    // 如果路径长度为0，不执行动画
    if (pathLength === 0) {
      return;
    }

    // 应用缓动函数
    const easedProgress = easing(progress);
    
    // 计算目标dashOffset
    const targetOffset = pathLength * (1 - easedProgress);
    
    // 平滑过渡到目标值
    const animate = () => {
      setDashOffset(targetOffset);
      setAnimatedProgress(easedProgress);
      
      // 检查是否正在动画
      if (easedProgress > 0 && easedProgress < 1) {
        setIsAnimating(true);
      } else {
        setIsAnimating(false);
      }
    };

    // 如果有延迟，使用setTimeout
    if (delay > 0 && progress === 0) {
      const timeoutId = setTimeout(animate, delay);
      return () => clearTimeout(timeoutId);
    } else {
      animate();
    }

    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [progress, pathLength, delay, easing]);

  return {
    dashOffset,
    animatedProgress,
    isAnimating,
  };
}

/**
 * 预定义的缓动函数
 */
export const easingFunctions = {
  linear: (t: number) => t,
  easeIn: (t: number) => t * t,
  easeOut: (t: number) => 1 - Math.pow(1 - t, 2),
  easeInOut: (t: number) => t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2,
  easeOutCubic: (t: number) => 1 - Math.pow(1 - t, 3),
  easeInOutCubic: (t: number) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
};

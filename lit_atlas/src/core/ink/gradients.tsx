/**
 * 渐变管理器
 * 管理SVG渐变定义和复用
 * 参考：@docs/design/ink_line_component_20251215.md
 */

import React from 'react';

/**
 * 创建渐变ID
 */
export function createGradientId(routeId: string): string {
  return `ink-gradient-${routeId}`;
}

/**
 * 渐变组件属性
 */
export interface InkGradientProps {
  id: string;
  color: string;
  direction?: 'horizontal' | 'vertical';
  opacity?: number;
}

/**
 * 墨迹渐变组件
 */
export function InkGradient({
  id,
  color,
  direction = 'horizontal',
  opacity = 1,
}: InkGradientProps) {
  const x1 = direction === 'horizontal' ? '0%' : '50%';
  const y1 = direction === 'horizontal' ? '50%' : '0%';
  const x2 = direction === 'horizontal' ? '100%' : '50%';
  const y2 = direction === 'horizontal' ? '50%' : '100%';

  return (
    <defs>
      <linearGradient id={id} x1={x1} y1={y1} x2={x2} y2={y2}>
        <stop offset="0%" stopColor={color} stopOpacity={opacity * 0.3} />
        <stop offset="50%" stopColor={color} stopOpacity={opacity} />
        <stop offset="100%" stopColor={color} stopOpacity={opacity * 0.6} />
      </linearGradient>
    </defs>
  );
}

/**
 * 渐变管理器类
 */
export class GradientManager {
  private gradients = new Map<string, string>();

  /**
   * 注册渐变
   */
  register(routeId: string, color: string): string {
    const id = createGradientId(routeId);
    this.gradients.set(routeId, id);
    return id;
  }

  /**
   * 获取渐变ID
   */
  get(routeId: string): string | undefined {
    return this.gradients.get(routeId);
  }

  /**
   * 检查是否已注册
   */
  has(routeId: string): boolean {
    return this.gradients.has(routeId);
  }

  /**
   * 清除所有渐变
   */
  clear(): void {
    this.gradients.clear();
  }

  /**
   * 获取所有渐变ID
   */
  getAllIds(): string[] {
    return Array.from(this.gradients.values());
  }
}

/**
 * 全局渐变管理器实例
 */
export const gradientManager = new GradientManager();

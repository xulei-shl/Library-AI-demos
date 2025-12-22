/**
 * 节点Tooltip组件
 * 显示城市和馆藏信息
 * 参考：@docs/design/ripple_node_component_20251215.md
 */

import React from 'react';
import { motion } from 'framer-motion';

/**
 * Tooltip属性
 */
export interface NodeTooltipProps {
  cityName: string;
  year?: number;
  hasCollection: boolean;
  collectionMeta?: {
    title: string;
    date: string;
    location: string;
  };
  position?: 'top' | 'bottom' | 'left' | 'right';
  coordinates: [number, number];
  // Overlay 模式支持
  overlayMode?: boolean;
  secondaryYear?: number;
  secondaryColor?: string;
}

/**
 * NodeTooltip组件
 */
export function NodeTooltip({
  cityName,
  year,
  hasCollection,
  collectionMeta,
  position = 'top',
  coordinates,
  overlayMode = false,
  secondaryYear,
  secondaryColor,
}: NodeTooltipProps) {
  const [x, y] = coordinates;
  
  // 计算Tooltip位置偏移
  const getOffset = (): { x: number; y: number } => {
    const offset = 20;
    switch (position) {
      case 'top':
        return { x: 0, y: -offset };
      case 'bottom':
        return { x: 0, y: offset };
      case 'left':
        return { x: -offset, y: 0 };
      case 'right':
        return { x: offset, y: 0 };
      default:
        return { x: 0, y: -offset };
    }
  };

  const offset = getOffset();
  const tooltipX = x + offset.x;
  const tooltipY = y + offset.y;

  // 计算高度（Overlay 模式下需要更高）
  const tooltipHeight = hasCollection && collectionMeta ? 70 : (overlayMode && secondaryYear ? 55 : 40);

  // 计算对齐方式
  const getAlignment = (): 'start' | 'middle' | 'end' => {
    switch (position) {
      case 'left':
        return 'end';
      case 'right':
        return 'start';
      default:
        return 'middle';
    }
  };

  return (
    <motion.g
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.8 }}
      transition={{ duration: 0.2 }}
    >
      {/* 背景 */}
      <rect
        x={tooltipX - 60}
        y={tooltipY - 30}
        width={120}
        height={tooltipHeight}
        fill="white"
        fillOpacity={0.95}
        stroke="#333"
        strokeWidth={1}
        rx={4}
        style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))' }}
      />
      
      {/* 城市名称 */}
      <text
        x={tooltipX}
        y={tooltipY - 15}
        textAnchor={getAlignment()}
        fontSize={14}
        fontWeight="bold"
        fill="#333"
      >
        {cityName}
      </text>
      
      {/* 年份 */}
      {year && (
        <text
          x={tooltipX}
          y={tooltipY}
          textAnchor={getAlignment()}
          fontSize={12}
          fill="#666"
        >
          {overlayMode && secondaryYear ? `主: ${year}年` : `${year}年`}
        </text>
      )}
      
      {/* 副作者年份（Overlay 模式） */}
      {overlayMode && secondaryYear && (
        <text
          x={tooltipX}
          y={tooltipY + 15}
          textAnchor={getAlignment()}
          fontSize={12}
          fill={secondaryColor || '#e74c3c'}
        >
          副: {secondaryYear}年
        </text>
      )}
      
      {/* 馆藏信息 */}
      {hasCollection && collectionMeta && (
        <>
          <text
            x={tooltipX}
            y={tooltipY + (overlayMode && secondaryYear ? 30 : 15)}
            textAnchor={getAlignment()}
            fontSize={11}
            fill="#2563eb"
            fontWeight="500"
          >
            📚 {collectionMeta.title}
          </text>
          <text
            x={tooltipX}
            y={tooltipY + (overlayMode && secondaryYear ? 45 : 30)}
            textAnchor={getAlignment()}
            fontSize={10}
            fill="#888"
          >
            {collectionMeta.date}
          </text>
        </>
      )}
      
      {/* 连接线 */}
      <line
        x1={x}
        y1={y}
        x2={tooltipX}
        y2={tooltipY - (tooltipHeight - 10)}
        stroke="#333"
        strokeWidth={1}
        strokeDasharray="2,2"
        opacity={0.3}
      />
    </motion.g>
  );
}

/**
 * 个人星图叠加层组件
 * 参考：@docs/design/personal_constellation_module_20251215.md
 */

'use client';

import React from 'react';
import { useConstellationStore } from './constellationStore';
import { COLORS } from '@/core/theme';

interface ConstellationOverlayProps {
  // 节点位置映射 (cityId -> [x, y])
  nodePositions: Map<string, [number, number]>;
  // 当前作者 ID
  currentAuthorId: string | null;
}

/**
 * 个人星图叠加层
 * 在地图上渲染用户标记的节点高亮
 */
export function ConstellationOverlay({
  nodePositions,
  currentAuthorId,
}: ConstellationOverlayProps) {
  const { marks, visible, enabled } = useConstellationStore();

  if (!visible || !enabled || !currentAuthorId) {
    return null;
  }

  // 筛选当前作者的标记
  const currentMarks = marks.filter((m) => m.authorId === currentAuthorId);

  return (
    <g className="constellation-overlay" style={{ mixBlendMode: 'screen' }}>
      {currentMarks.map((mark) => {
        const position = nodePositions.get(mark.cityId);
        if (!position) return null;

        const [x, y] = position;
        const isRead = mark.status === 'read';

        return (
          <g key={`${mark.authorId}-${mark.cityId}`}>
            {/* 外圈光晕 */}
            <circle
              cx={x}
              cy={y}
              r={12}
              fill="none"
              stroke={COLORS.constellation.glow}
              strokeWidth={2}
              opacity={0.6}
              className="constellation-glow"
            />
            
            {/* 内圈标记 */}
            <circle
              cx={x}
              cy={y}
              r={6}
              fill={isRead ? COLORS.constellation.read : COLORS.constellation.wish}
              opacity={0.9}
              className="constellation-mark"
            />

            {/* 已读标记：实心圆点 */}
            {isRead && (
              <circle
                cx={x}
                cy={y}
                r={3}
                fill={COLORS.constellation.glow}
                opacity={1}
              />
            )}
          </g>
        );
      })}

      <style jsx>{`
        .constellation-glow {
          animation: pulse 2s ease-in-out infinite;
        }

        .constellation-mark {
          transition: all 0.3s ease;
        }

        .constellation-mark:hover {
          opacity: 1;
          transform: scale(1.2);
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 0.4;
          }
          50% {
            opacity: 0.8;
          }
        }
      `}</style>
    </g>
  );
}

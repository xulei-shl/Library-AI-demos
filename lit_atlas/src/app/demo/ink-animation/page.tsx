/**
 * 墨迹动画演示页面
 * v0.4.0 - 展示墨迹生长、涟漪扩散等动画效果
 */

'use client';

import React from 'react';
import { OpenLayersMap } from '@/core/map/OpenLayersMap';
import { useAuthorStore } from '@/core/state/authorStore';
import { usePlaybackStore } from '@/core/state/playbackStore';

export default function InkAnimationDemo() {
  const { currentAuthor } = useAuthorStore();
  const { isPlaying, currentTime, play, pause, setCurrentTime } = usePlaybackStore();

  return (
    <div className="relative h-screen w-screen bg-gray-900">
      {/* 地图容器 */}
      <OpenLayersMap
        className="absolute inset-0"
        showControls={true}
        onLocationClick={(location) => {
          console.log('Location clicked:', location);
        }}
      />

      {/* 控制面板 */}
      <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-4 max-w-sm">
        <h2 className="text-lg font-bold mb-3 text-gray-800">
          墨迹动画演示 v0.4.0
        </h2>

        {/* 作者信息 */}
        {currentAuthor && (
          <div className="mb-4 pb-4 border-b border-gray-200">
            <p className="text-sm text-gray-600">当前作者</p>
            <p className="text-base font-semibold text-gray-800">
              {currentAuthor.name}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {currentAuthor.works?.length || 0} 部作品
            </p>
          </div>
        )}

        {/* 播放控制 */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => (isPlaying ? pause() : play())}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              {isPlaying ? '⏸ 暂停' : '▶ 播放'}
            </button>
            <button
              onClick={() => setCurrentTime(0)}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
            >
              ⏮ 重置
            </button>
          </div>

          {/* 时间轴 */}
          <div>
            <label className="text-xs text-gray-600 block mb-1">
              时间轴: {Math.floor(currentTime / 1000)}s
            </label>
            <input
              type="range"
              min="0"
              max="10000"
              step="100"
              value={currentTime}
              onChange={(e) => setCurrentTime(Number(e.target.value))}
              className="w-full"
            />
          </div>
        </div>

        {/* 动画说明 */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            动画效果
          </h3>
          <ul className="text-xs text-gray-600 space-y-1">
            <li>🎨 <span className="text-red-600">朱砂</span> - 生长中的路径</li>
            <li>🎨 <span className="text-blue-800">黛蓝</span> - 历史路径</li>
            <li>🎨 <span className="text-teal-600">松石</span> - 涟漪扩散</li>
            <li>✨ 呼吸灯 - 常亮节点光晕</li>
            <li>📏 动态线宽 - 模拟毛笔压感</li>
          </ul>
        </div>
      </div>

      {/* 图例 */}
      <div className="absolute bottom-4 right-4 bg-white/90 backdrop-blur-sm rounded-lg shadow-lg p-3">
        <h3 className="text-xs font-semibold text-gray-700 mb-2">
          中国传统色
        </h3>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-[#b03d46]"></div>
            <span className="text-xs text-gray-600">朱砂 - 活跃</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-[#1D3557]"></div>
            <span className="text-xs text-gray-600">黛蓝 - 历史</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-[#457B9D]"></div>
            <span className="text-xs text-gray-600">松石 - 涟漪</span>
          </div>
        </div>
      </div>
    </div>
  );
}

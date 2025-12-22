'use client';

import { useEffect } from 'react';
import { OpenLayersMap } from '@/core/map/OpenLayersMap';
import { useAuthorStore } from '@/core/state/authorStore';
import { usePlaybackStore } from '@/core/state/playbackStore';

/**
 * 《墨迹与边界》主页面
 * Sprint 1 演示：数据加载与地图渲染
 */
export default function Home() {
  const { loadAuthor, currentAuthor, isLoading, error } = useAuthorStore();
  const { isPlaying, togglePlayPause } = usePlaybackStore();

  // 自动加载鲁迅的数据
  useEffect(() => {
    loadAuthor('lu_xun').catch(err => {
      console.error('加载作者数据失败:', err);
    });
  }, [loadAuthor]);

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      {/* 全屏地图背景 */}
      <OpenLayersMap showControls={true} />

      {/* 顶部标题栏 - 浮动在地图上 */}
      <header className="absolute top-0 left-0 right-0 z-20 border-b border-white/10 bg-black/60 backdrop-blur-md">
        <div className="container mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-white">
            墨迹与边界 · Ink & Boundaries
          </h1>
          <p className="text-sm text-gray-300">
            现代中国作家的地理叙事可视化
          </p>
        </div>
      </header>

      {/* 加载状态 - 居中覆盖 */}
      {isLoading && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="text-center">
            <div className="mb-4 text-lg text-white">加载作者数据中...</div>
          </div>
        </div>
      )}

      {/* 错误状态 - 居中覆盖 */}
      {error && (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="rounded-lg bg-red-900/80 p-6 text-center backdrop-blur-sm">
            <div className="mb-2 text-lg font-semibold text-red-100">
              加载失败
            </div>
            <div className="text-sm text-red-200">{error}</div>
          </div>
        </div>
      )}

      {/* 左侧信息面板 - 浮动 */}
      {!isLoading && !error && currentAuthor && (
        <div className="absolute left-6 top-24 z-20 max-w-sm rounded-lg bg-black/70 p-4 text-white shadow-2xl backdrop-blur-md">
          <div className="text-sm text-gray-400">当前作者</div>
          <div className="mt-1 text-xl font-semibold">{currentAuthor.name}</div>
          <div className="mt-2 text-sm text-gray-300">
            {currentAuthor.works.length} 部作品
          </div>
          
          {/* 动画说明 */}
          <div className="mt-4 border-t border-white/20 pt-3">
            <div className="text-xs text-gray-400 mb-2">动画效果</div>
            <div className="space-y-1 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#b03d46]"></div>
                <span className="text-gray-300">朱砂 - 生长路径</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#1D3557]"></div>
                <span className="text-gray-300">黛蓝 - 历史路径</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[#457B9D]"></div>
                <span className="text-gray-300">松石 - 涟漪扩散</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 播放控制面板 - 右下角浮动 */}
      {!isLoading && !error && (
        <div className="absolute bottom-8 right-8 z-20 rounded-lg bg-black/70 p-4 text-white shadow-2xl backdrop-blur-md">
          <div className="flex items-center gap-3">
            {/* 播放/暂停按钮 */}
            <button
              onClick={togglePlayPause}
              className="rounded-full bg-[#b03d46] px-6 py-3 text-sm font-medium text-white shadow-lg transition-all hover:bg-[#c04d56] hover:scale-105"
            >
              {isPlaying ? '⏸ 暂停' : '▶ 播放'}
            </button>
            
            {/* 重置按钮 */}
            <button
              onClick={() => {
                usePlaybackStore.getState().stop();
              }}
              className="rounded-full bg-gray-700 px-4 py-3 text-sm font-medium text-white shadow-lg transition-all hover:bg-gray-600"
            >
              ⏹ 重置
            </button>
          </div>
          
          {/* 时间显示 */}
          <div className="mt-2 text-xs text-gray-400">
            {usePlaybackStore.getState().getFormattedTime()}
          </div>
        </div>
      )}

      {/* 底部信息 - 浮动 */}
      <footer className="absolute bottom-0 left-0 right-0 z-20 border-t border-white/10 bg-black/60 py-3 text-center text-sm text-gray-400 backdrop-blur-md">
        <p>
          v0.4.0 墨迹动画版 · 参考设计：
          <a
            href="/docs/墨迹与边界-0.4.md"
            className="ml-2 text-[#b03d46] hover:underline"
          >
            墨迹与边界-0.4.md
          </a>
        </p>
      </footer>
    </div>
  );
}

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
        </div>
      )}

      {/* 播放控制按钮 - 右下角浮动 */}
      {!isLoading && !error && (
        <button
          onClick={togglePlayPause}
          className="absolute bottom-8 right-8 z-20 rounded-full bg-[#8B4513] px-6 py-3 text-sm font-medium text-white shadow-2xl transition-all hover:bg-[#A0522D] hover:scale-105"
        >
          {isPlaying ? '⏸ 暂停' : '▶ 播放'}
        </button>
      )}

      {/* 底部信息 - 浮动 */}
      <footer className="absolute bottom-0 left-0 right-0 z-20 border-t border-white/10 bg-black/60 py-3 text-center text-sm text-gray-400 backdrop-blur-md">
        <p>
          参考设计文档：
          <a
            href="/docs/墨迹与边界-0.3.md"
            className="ml-2 text-[#A0522D] hover:underline"
          >
            墨迹与边界-0.3.md
          </a>
        </p>
      </footer>
    </div>
  );
}

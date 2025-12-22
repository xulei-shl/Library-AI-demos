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
    <div className="flex min-h-screen flex-col bg-[#f5f1e8]">
      {/* 顶部标题栏 */}
      <header className="border-b border-[#c4bfb0] bg-white/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-[#3d3d3d]">
            墨迹与边界 · Ink & Boundaries
          </h1>
          <p className="text-sm text-[#666]">
            现代中国作家的地理叙事可视化
          </p>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="flex flex-1 flex-col items-center justify-center p-8">
        {/* 加载状态 */}
        {isLoading && (
          <div className="text-center">
            <div className="mb-4 text-lg text-[#666]">加载作者数据中...</div>
          </div>
        )}

        {/* 错误状态 */}
        {error && (
          <div className="rounded-lg bg-red-50 p-6 text-center">
            <div className="mb-2 text-lg font-semibold text-red-800">
              加载失败
            </div>
            <div className="text-sm text-red-600">{error}</div>
          </div>
        )}

        {/* 地图容器 */}
        {!isLoading && !error && (
          <div className="w-full max-w-6xl">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm text-[#666]">
                {currentAuthor ? (
                  <>
                    当前作者：
                    <span className="font-semibold text-[#3d3d3d]">
                      {currentAuthor.name}
                    </span>
                    {' · '}
                    {currentAuthor.works.length} 部作品
                  </>
                ) : (
                  '等待加载作者数据...'
                )}
              </div>

              {/* 简单的播放控制 */}
              <button
                onClick={togglePlayPause}
                className="rounded-lg bg-[#8B4513] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#A0522D]"
              >
                {isPlaying ? '⏸ 暂停' : '▶ 播放'}
              </button>
            </div>

            {/* 地图组件 - 全屏 */}
            <div className="overflow-hidden rounded-lg border border-gray-800 shadow-2xl" style={{ height: '800px' }}>
              <OpenLayersMap
                showControls={true}
              />
            </div>

            {/* 提示信息 */}
            <div className="mt-4 text-center text-sm text-[#999]">
              Sprint 1 演示 · 数据加载与地图渲染基础功能
            </div>
          </div>
        )}
      </main>

      {/* 底部信息 */}
      <footer className="border-t border-[#c4bfb0] bg-white/80 py-4 text-center text-sm text-[#999]">
        <p>
          参考设计文档：
          <a
            href="/docs/墨迹与边界-0.3.md"
            className="ml-2 text-[#8B4513] hover:underline"
          >
            墨迹与边界-0.3.md
          </a>
        </p>
      </footer>
    </div>
  );
}

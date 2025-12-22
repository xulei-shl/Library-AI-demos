'use client';

import { useEffect } from 'react';
import { OpenLayersMap } from '@/core/map/OpenLayersMap';
import { useAuthorStore } from '@/core/state/authorStore';
import { InkPanel } from '@/core/ink/InkPanel';
import { AnimatePresence, motion } from 'framer-motion';

/**
 * 《墨迹与边界》主页面
 * v0.4.0: 墨迹风格重构
 */
export default function Home() {
  const { loadAuthor, currentAuthor, isLoading, error } = useAuthorStore();

  // 自动加载鲁迅的数据
  useEffect(() => {
    loadAuthor('lu_xun').catch(err => {
      console.error('加载作者数据失败:', err);
    });
  }, [loadAuthor]);

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#1a1a1a] font-serif">
      {/* 全屏地图背景 */}
      <div className="absolute inset-0 z-0">
        <OpenLayersMap showControls={false} />
      </div>

      {/* 顶部标题栏 */}
      <header className="absolute top-0 left-0 right-0 z-20 pointer-events-none p-6">
        <div className="flex justify-between items-start">
          <InkPanel variant="dark" className="pointer-events-auto px-6 py-4 min-w-[300px]">
            <h1 className="text-2xl font-bold text-white tracking-wider">
              墨迹与边界
            </h1>
            <p className="text-sm text-gray-400 font-sans mt-1">
              Ink & Boundaries v0.4.0
            </p>
          </InkPanel>

          {/* 右上角：项目链接 */}
          <InkPanel variant="glass" className="pointer-events-auto px-4 py-2">
            <a
              href="/docs/墨迹与边界-0.4.md"
              className="text-sm text-white/80 hover:text-white transition-colors"
            >
              设计文档
            </a>
          </InkPanel>
        </div>
      </header>

      {/* 左侧信息面板 */}
      <AnimatePresence mode="wait">
        {!isLoading && !error && currentAuthor && (
          <div className="absolute left-6 top-32 z-20 w-80 pointer-events-none">
            <InkPanel variant="dark" className="pointer-events-auto p-6 space-y-6">
              {/* 作者信息 */}
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-widest mb-2">Current Author</div>
                <div className="text-3xl font-bold text-white mb-1">{currentAuthor.name}</div>
                <div className="text-sm text-gray-400 font-sans">
                  {currentAuthor.works.length} Works Collected
                </div>
              </div>

              {/* 装饰线 */}
              <div className="h-px w-full bg-gradient-to-r from-white/20 to-transparent" />

              {/* 图例 */}
              <div className="space-y-3">
                <div className="text-xs text-gray-500 uppercase tracking-widest mb-2">Legend</div>
                <div className="space-y-2 font-sans text-xs">
                  <div className="flex items-center gap-3 group cursor-help">
                    <div className="w-2 h-2 rounded-full bg-[#00FFFF] shadow-[0_0_8px_#00FFFF]" />
                    <span className="text-gray-300 group-hover:text-white transition-colors">Active Path (Neon Cyan)</span>
                  </div>
                  <div className="flex items-center gap-3 group cursor-help">
                    <div className="w-2 h-2 rounded-full bg-[#4682B4] shadow-[0_0_8px_#4682B4]" />
                    <span className="text-gray-300 group-hover:text-white transition-colors">History Path (Steel Blue)</span>
                  </div>
                  <div className="flex items-center gap-3 group cursor-help">
                    <div className="w-2 h-2 rounded-full bg-[#FF1493] shadow-[0_0_8px_#FF1493]" />
                    <span className="text-gray-300 group-hover:text-white transition-colors">Cultural Ripple (Deep Pink)</span>
                  </div>
                </div>
              </div>
            </InkPanel>
          </div>
        )}
      </AnimatePresence>

      {/* 加载/错误状态 */}
      <AnimatePresence>
        {(isLoading || error) && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          >
            <InkPanel variant="dark" className="p-8 text-center min-w-[300px]">
              {isLoading ? (
                <div className="space-y-4">
                  <div className="w-12 h-12 border-2 border-[#b03d46] border-t-transparent rounded-full animate-spin mx-auto" />
                  <div className="text-lg text-white font-serif">Loading Archives...</div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-[#b03d46] text-4xl">!</div>
                  <div className="text-lg text-white font-serif">Connection Failed</div>
                  <div className="text-sm text-red-300">{error}</div>
                </div>
              )}
            </InkPanel>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

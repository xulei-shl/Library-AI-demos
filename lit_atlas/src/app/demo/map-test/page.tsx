'use client';

import { useEffect } from 'react';
import { OpenLayersMap } from '@/core/map/OpenLayersMap';
import { useAuthorStore } from '@/core/state/authorStore';

/**
 * OpenLayers 地图测试页面
 * 用于验证新地图系统的功能
 */
export default function MapTestPage() {
  const { loadAuthor } = useAuthorStore();

  // 加载测试数据
  useEffect(() => {
    console.info('[MapTestPage] 加载测试数据');
    
    // 这里应该加载真实的作者数据
    // 暂时使用 mock 数据进行测试
    loadAuthor('test-author-id');
  }, [loadAuthor]);

  return (
    <div className="w-full h-screen">
      {/* 全屏地图 */}
      <OpenLayersMap
        showControls={true}
        onLocationClick={(location) => {
          console.log('[MapTestPage] 位置点击:', location);
        }}
      />
    </div>
  );
}

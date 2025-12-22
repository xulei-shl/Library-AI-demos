'use client';

import React from 'react';
import { OpenLayersMap } from '@/core/map/OpenLayersMap';

/**
 * 点阵地图演示页面
 */
export default function MapV2DemoPage() {
  const handleLocationClick = (location: any) => {
    console.log('点击位置:', location);
  };

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-8">
      <div className="mb-6 text-center">
        <h1 className="text-3xl font-bold text-white mb-2">
          OpenLayers 交互式地图
        </h1>
        <p className="text-gray-400">
          全屏交互式地图，支持缩放、平移等操作
        </p>
      </div>

      <div className="border border-gray-700 rounded-lg overflow-hidden shadow-2xl" style={{ height: '700px' }}>
        <OpenLayersMap
          showControls={true}
          onLocationClick={handleLocationClick}
        />
      </div>

      <div className="mt-6 text-gray-400 text-sm text-center max-w-2xl">
        <p>
          这是一个使用 OpenLayers 实现的交互式地图。
          支持缩放、平移、点击等交互操作，数据层基于作品的出版城市坐标渲染。
        </p>
      </div>
    </div>
  );
}

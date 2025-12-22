'use client';

import { OpenLayersMap } from '@/core/map/OpenLayersMap';

/**
 * 地图演示页面
 */
export default function DemoPage() {
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold mb-2 text-gray-900">
          墨迹与边界 - 地图演示
        </h1>
        <p className="text-gray-600 mb-8">
          Natural Earth 投影 + 纸张纹理主题
        </p>
        
        <div className="bg-gray-900 rounded-lg shadow-2xl overflow-hidden" style={{ height: '700px' }}>
          <OpenLayersMap
            showControls={true}
          />
        </div>

        <div className="mt-8 grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">✅ Sprint 0 完成</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• 基础设施配置</li>
              <li>• 地理数据准备（50个城市）</li>
              <li>• UI 设计系统</li>
              <li>• 性能监控工具</li>
              <li>• 状态管理（Zustand + RxJS）</li>
              <li>• Geo 渲染基础（Natural Earth 投影）</li>
              <li>• 测试基线（26个测试通过）</li>
            </ul>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">🎯 下一步：Sprint 1</h3>
            <ul className="text-sm text-gray-600 space-y-1">
              <li>• 数据加载与规范化</li>
              <li>• 作者/播放状态管理</li>
              <li>• Smart FlyTo 相机控制</li>
              <li>• 集成测试</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

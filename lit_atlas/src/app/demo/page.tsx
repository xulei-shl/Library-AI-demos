'use client';

import React, { useEffect } from 'react';
import { SimpleMap } from '../../core/map/SimpleMap';
import { useAuthorStore } from '../../core/state/authorStore';
import { usePlaybackStore } from '../../core/state/playbackStore';

export default function DemoPage() {
  const { 
    currentAuthor, 
    loadAuthor, 
    isLoading, 
    error,
    availableAuthors 
  } = useAuthorStore();
  
  const { 
    isPlaying, 
    play, 
    pause, 
    stop,
    currentTime,
    getFormattedTime
  } = usePlaybackStore();

  // 预加载作者数据
  useEffect(() => {
    const authorIds = ['lu_xun', 'ba_jin'];
    authorIds.forEach(id => {
      loadAuthor(id).catch(err => {
        console.warn(`预加载作者 ${id} 失败:`, err);
      });
    });
  }, [loadAuthor]);

  const handleAuthorSelect = (authorId: string) => {
    loadAuthor(authorId).catch(err => {
      console.error('加载作者失败:', err);
    });
  };

  const handlePlayPause = () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            《墨迹与边界》- MVP演示
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            文学作品的地理叙事可视化平台
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* 侧边栏控制面板 */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow p-6 space-y-6">
              {/* 作者选择 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  选择作者
                </h3>
                <div className="space-y-2">
                  <button
                    onClick={() => handleAuthorSelect('lu_xun')}
                    className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                      currentAuthor?.id === 'lu_xun'
                        ? 'bg-blue-100 text-blue-800 border border-blue-200'
                        : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <div className="font-medium">鲁迅</div>
                    <div className="text-xs text-gray-500">
                      现代文学奠基人
                    </div>
                  </button>
                  
                  <button
                    onClick={() => handleAuthorSelect('ba_jin')}
                    className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
                      currentAuthor?.id === 'ba_jin'
                        ? 'bg-blue-100 text-blue-800 border border-blue-200'
                        : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <div className="font-medium">巴金</div>
                    <div className="text-xs text-gray-500">
                      激流三部曲作者
                    </div>
                  </button>
                </div>
              </div>

              {/* 播放控制 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  播放控制
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={handlePlayPause}
                      disabled={!currentAuthor}
                      className={`px-4 py-2 rounded-md font-medium transition-colors ${
                        currentAuthor
                          ? isPlaying
                            ? 'bg-red-600 hover:bg-red-700 text-white'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                    >
                      {isPlaying ? '暂停' : '播放'}
                    </button>
                    
                    <button
                      onClick={stop}
                      disabled={!currentAuthor}
                      className={`px-3 py-2 rounded-md font-medium transition-colors ${
                        currentAuthor
                          ? 'bg-gray-600 hover:bg-gray-700 text-white'
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                    >
                      停止
                    </button>
                  </div>
                  
                  {currentAuthor && (
                    <div className="text-sm text-gray-600">
                      <div>播放时间: {getFormattedTime()}</div>
                      <div className="text-xs text-gray-500">
                        {isPlaying ? '正在播放' : '已暂停'}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 作者信息 */}
              {currentAuthor && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 mb-3">
                    作者信息
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-medium text-gray-700">姓名:</span>
                      <span className="ml-2 text-gray-600">{currentAuthor.name}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">生卒年:</span>
                      <span className="ml-2 text-gray-600">
                        {currentAuthor.birth_year} - {currentAuthor.death_year}
                      </span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">作品数:</span>
                      <span className="ml-2 text-gray-600">{currentAuthor.works.length}</span>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">路线数:</span>
                      <span className="ml-2 text-gray-600">
                        {currentAuthor.works.reduce((sum, work) => sum + work.routes.length, 0)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="mt-3 p-3 bg-gray-50 rounded-md">
                    <p className="text-xs text-gray-600 leading-relaxed">
                      {currentAuthor.biography}
                    </p>
                  </div>
                </div>
              )}

              {/* 状态显示 */}
              <div>
                <h3 className="text-lg font-semibold text-gray-800 mb-3">
                  系统状态
                </h3>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span>加载状态:</span>
                    <span className={isLoading ? 'text-yellow-600' : 'text-green-600'}>
                      {isLoading ? '加载中' : '就绪'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>错误状态:</span>
                    <span className={error ? 'text-red-600' : 'text-green-600'}>
                      {error ? '有错误' : '正常'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>播放状态:</span>
                    <span className={isPlaying ? 'text-blue-600' : 'text-gray-600'}>
                      {isPlaying ? '播放中' : '已停止'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 地图区域 */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="mb-4">
                <h2 className="text-xl font-semibold text-gray-800 mb-2">
                  地理叙事地图
                </h2>
                <p className="text-sm text-gray-600">
                  点击地图上的国家或地区进行交互。选择作者后可以看到相关的文学创作轨迹。
                </p>
              </div>
              
              <div className="relative">
                <SimpleMap 
                  width={800} 
                  height={600}
                  className="border border-gray-200 rounded"
                />
                
                {/* 加载遮罩 */}
                {isLoading && (
                  <div className="absolute inset-0 bg-white bg-opacity-75 flex items-center justify-center rounded">
                    <div className="text-gray-600">正在加载地图数据...</div>
                  </div>
                )}
              </div>
              
              {/* 错误提示 */}
              {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                  <div className="text-red-800 text-sm">
                    <strong>错误:</strong> {error}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 功能说明 */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            MVP功能说明
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            <div className="p-3 bg-blue-50 rounded-md">
              <h3 className="font-semibold text-blue-800 mb-2">✓ 已实现</h3>
              <ul className="text-blue-700 space-y-1">
                <li>• 基础地图渲染</li>
                <li>• 作者数据加载</li>
                <li>• 状态管理</li>
                <li>• 播放控制</li>
              </ul>
            </div>
            
            <div className="p-3 bg-yellow-50 rounded-md">
              <h3 className="font-semibold text-yellow-800 mb-2">⏳ 开发中</h3>
              <ul className="text-yellow-700 space-y-1">
                <li>• 动画路线渲染</li>
                <li>• 相机控制</li>
                <li>• 交互优化</li>
                <li>• 性能调优</li>
              </ul>
            </div>
            
            <div className="p-3 bg-gray-50 rounded-md">
              <h3 className="font-semibold text-gray-800 mb-2">📋 计划中</h3>
              <ul className="text-gray-700 space-y-1">
                <li>• InkLine动画</li>
                <li>• Ripple节点</li>
                <li>• Overlay模式</li>
                <li>• 个人星图</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
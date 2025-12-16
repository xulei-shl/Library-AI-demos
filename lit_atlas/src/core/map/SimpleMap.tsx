import React, { useRef, useEffect, useState } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { useAuthorStore } from '../state/authorStore';
import { usePlaybackStore } from '../state/playbackStore';

// 简化的地图组件，先让MVP跑起来
const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

interface SimpleMapProps {
  width?: number;
  height?: number;
  className?: string;
}

export function SimpleMap({ 
  width = 800, 
  height = 600, 
  className = '' 
}: SimpleMapProps) {
  const { currentAuthor, isLoading } = useAuthorStore();
  const { isPlaying } = usePlaybackStore();
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);

  const handleCountryClick = (geo: any) => {
    setSelectedCountry(geo.properties.NAME);
    console.log('点击国家:', geo.properties.NAME);
  };

  if (isLoading) {
    return (
      <div className={`simple-map ${className}`} style={{ width, height }}>
        <div className="flex items-center justify-center h-full bg-gray-100">
          <div className="text-gray-600">加载地图中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`simple-map relative ${className}`} style={{ width, height }}>
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          scale: 120,
          center: [105, 35] // 中国中心
        }}
        width={width}
        height={height}
      >
        <Geographies geography={geoUrl}>
          {({ geographies }) =>
            geographies.map((geo) => (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                onClick={() => handleCountryClick(geo)}
                style={{
                  default: {
                    fill: selectedCountry === geo.properties.NAME ? '#e0e7ff' : '#f0f0f0',
                    stroke: '#d0d0d0',
                    strokeWidth: 0.5,
                    outline: 'none',
                    cursor: 'pointer'
                  },
                  hover: {
                    fill: '#e0e0e0',
                    stroke: '#d0d0d0',
                    strokeWidth: 0.5,
                    outline: 'none'
                  },
                  pressed: {
                    fill: '#d0d0d0',
                    stroke: '#d0d0d0',
                    strokeWidth: 0.5,
                    outline: 'none'
                  }
                }}
              />
            ))
          }
        </Geographies>
      </ComposableMap>

      {/* 作者信息覆盖层 */}
      {currentAuthor && (
        <div className="absolute top-4 left-4 bg-white bg-opacity-90 p-4 rounded shadow-lg max-w-sm">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">
            {currentAuthor.name}
          </h2>
          <div className="text-sm text-gray-600 space-y-1">
            <div>作品数量: {currentAuthor.works.length}</div>
            <div className="text-xs text-gray-500">
              {currentAuthor.biography?.substring(0, 100)}...
            </div>
            {isPlaying && (
              <div className="flex items-center mt-2 text-blue-600">
                <div className="w-2 h-2 bg-blue-600 rounded-full mr-2 animate-pulse"></div>
                <span className="text-xs">正在播放</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 控制提示 */}
      <div className="absolute bottom-4 right-4 bg-black bg-opacity-75 text-white px-3 py-2 rounded text-sm">
        点击地图选择区域
      </div>

      {/* 选中国家信息 */}
      {selectedCountry && (
        <div className="absolute top-4 right-4 bg-white bg-opacity-90 p-4 rounded shadow-lg">
          <h3 className="font-semibold">选中的国家/地区:</h3>
          <p className="text-sm text-gray-700">{selectedCountry}</p>
          <button 
            onClick={() => setSelectedCountry(null)}
            className="mt-2 text-xs text-blue-600 hover:text-blue-800"
          >
            清除选择
          </button>
        </div>
      )}
    </div>
  );
}
import React, { useRef, useEffect, useState, useCallback } from 'react';
import { ComposableMap, Geographies, Geography } from 'react-simple-maps';
import { motion, AnimatePresence } from 'framer-motion';
import { CameraController } from './cameraController';
import { useViewportInteraction, InteractionMode } from './useViewportInteraction';
import { LayerType, DEFAULT_LAYERS, optimizeLayers } from './layers';
import { useAuthorStore } from '../state/authorStore';
import { usePlaybackStore } from '../state/playbackStore';

// 地图配置
const geoUrl = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

/**
 * NarrativeMap组件属性
 */
export interface NarrativeMapProps {
  width?: number;
  height?: number;
  className?: string;
  showControls?: boolean;
  interactionMode?: InteractionMode;
  onViewportChange?: (cameraState: any) => void;
  onLocationClick?: (location: any) => void;
}

/**
 * NarrativeMap主组件
 */
export function NarrativeMap({
  width = 800,
  height = 600,
  className = '',
  showControls = true,
  interactionMode = InteractionMode.AUTO,
  onViewportChange,
  onLocationClick
}: NarrativeMapProps) {
  // 状态管理
  const containerRef = useRef<HTMLDivElement>(null);
  const [cameraController, setCameraController] = useState<CameraController | null>(null);
  const [cameraState, setCameraState] = useState({
    center: [105, 35] as [number, number],
    zoom: 1
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Store hooks
  const { currentAuthor, isLoading: authorLoading } = useAuthorStore();
  const { isPlaying, currentTime } = usePlaybackStore();

  // 初始化相机控制器
  useEffect(() => {
    if (containerRef.current) {
      const controller = new CameraController(width, height, 50);
      setCameraController(controller);
      setIsLoading(false);
      console.info('相机控制器初始化完成');
    }
  }, [width, height]);

  // 视口交互
  const {
    isInteractionEnabled,
    enableInteraction
  } = useViewportInteraction(containerRef, {
    mode: interactionMode,
    enableZoom: true,
    enablePan: true,
    enableRotate: false
  });

  // 处理作者数据变化
  useEffect(() => {
    if (currentAuthor && cameraController) {
      // 计算作者作品的边界盒
      const bbox = calculateAuthorBBox(currentAuthor);
      
      // 执行智能飞行动画
      const flyToParams = cameraController.calculateSmartFlyTo(bbox, 0.1, 1500);
      cameraController.flyTo(flyToParams, (state) => {
        setCameraState({
          center: state.center,
          zoom: state.zoom
        });
      });
      
      console.info(`自动聚焦到作者: ${currentAuthor.name}`);
    }
  }, [currentAuthor, cameraController]);

  // 计算作者边界盒
  const calculateAuthorBBox = useCallback((author: any) => {
    if (!author.works || author.works.length === 0) {
      return { west: 70, east: 140, south: 15, north: 55 }; // 默认中国范围
    }

    const coordinates: [number, number][] = [];
    
    author.works.forEach((work: any) => {
      if (work.routes) {
        work.routes.forEach((route: any) => {
          if (route.start_location?.coordinates) {
            coordinates.push([
              route.start_location.coordinates.lng,
              route.start_location.coordinates.lat
            ]);
          }
          if (route.end_location?.coordinates) {
            coordinates.push([
              route.end_location.coordinates.lng,
              route.end_location.coordinates.lat
            ]);
          }
        });
      }
    });

    if (coordinates.length === 0) {
      return { west: 70, east: 140, south: 15, north: 55 };
    }

    const lons = coordinates.map(coord => coord[0]);
    const lats = coordinates.map(coord => coord[1]);
    
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);

    // 添加缓冲区
    const lonPadding = (maxLon - minLon) * 0.2;
    const latPadding = (maxLat - minLat) * 0.2;

    return {
      west: minLon - lonPadding,
      east: maxLon + lonPadding,
      south: minLat - latPadding,
      north: maxLat + latPadding
    };
  }, []);

  // 处理地理位置点击
  const handleGeographyClick = useCallback((geo: any) => {
    const location = {
      id: geo.id,
      properties: geo.properties,
      coordinates: geo.geometry.coordinates
    };
    
    onLocationClick?.(location);
    
    if (!isInteractionEnabled) {
      enableInteraction();
    }
  }, [isInteractionEnabled, enableInteraction, onLocationClick]);

  // 优化图层配置
  const optimizedLayers = optimizeLayers(DEFAULT_LAYERS);

  // 渲染加载状态
  if (isLoading || authorLoading) {
    return (
      <div className={`narrative-map ${className}`} style={{ width, height }}>
        <div className="flex items-center justify-center h-full bg-gray-100">
          <div className="text-gray-600">加载地图数据中...</div>
        </div>
      </div>
    );
  }

  // 渲染错误状态
  if (error) {
    return (
      <div className={`narrative-map ${className}`} style={{ width, height }}>
        <div className="flex items-center justify-center h-full bg-red-50">
          <div className="text-red-600">地图加载失败: {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`narrative-map relative overflow-hidden ${className}`}
      style={{ width, height }}
    >
      {/* SVG 地图容器 */}
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          scale: cameraState.zoom * 150,
          center: cameraState.center
        }}
        width={width}
        height={height}
      >
        <Geographies geography={geoUrl}>
          {({ geographies }: { geographies: any[] }) =>
            geographies.map((geo) => (
              <Geography
                key={geo.rsmKey}
                geography={geo}
                onClick={() => handleGeographyClick(geo)}
                style={{
                  default: {
                    fill: '#f0f0f0',
                    stroke: '#d0d0d0',
                    strokeWidth: 0.5,
                    outline: 'none'
                  },
                  hover: {
                    fill: isInteractionEnabled ? '#e0e0e0' : '#f0f0f0',
                    stroke: '#d0d0d0',
                    strokeWidth: 0.5,
                    outline: 'none',
                    cursor: isInteractionEnabled ? 'pointer' : 'default'
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

      {/* 覆盖层渲染区域 */}
      <AnimatePresence>
        {currentAuthor && (
          <motion.div
            className="absolute inset-0 pointer-events-none"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="text-sm text-gray-600 absolute top-4 left-4 bg-white bg-opacity-90 p-2 rounded">
              <div className="font-semibold">{currentAuthor.name}</div>
              <div className="text-xs">
                {currentAuthor.works.length} 部作品
                {isPlaying && (
                  <span className="ml-2 text-blue-600">● 播放中</span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 交互控制提示 */}
      {!isInteractionEnabled && (
        <div className="absolute bottom-4 right-4 bg-black bg-opacity-75 text-white px-3 py-2 rounded text-sm">
          点击启用手动控制
        </div>
      )}

      {/* 播放控制覆盖层 */}
      {showControls && (
        <div className="absolute bottom-4 left-4">
          {/* 这里可以添加播放控制组件 */}
        </div>
      )}
    </div>
  );
}
/**
 * OpenLayers 地图组件 - 全屏交互式地图
 * 
 * 功能：
 * - 全屏地图渲染（非局限在小窗框）
 * - 基于作品出版城市坐标的数据可视化
 * - 支持缩放、平移等交互
 * - 集成播放控制和动画效果
 */

import React, { useRef, useEffect, useState } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import VectorSource from 'ol/source/Vector';
import StadiaMaps from 'ol/source/StadiaMaps';
import { fromLonLat } from 'ol/proj';
import { defaults as defaultControls } from 'ol/control';
import { Style, Circle, Fill, Stroke } from 'ol/style';
import type { FeatureLike } from 'ol/Feature';

import { useAuthorStore } from '../state/authorStore';
import { usePlaybackStore } from '../state/playbackStore';
import { convertAuthorToFeatures, isCityFeature, isRouteFeature } from './utils/featureConverter';

import 'ol/ol.css';

/**
 * 地图组件属性
 */
export interface OpenLayersMapProps {
  className?: string;
  showControls?: boolean;
  onLocationClick?: (location: any) => void;
}

/**
 * OpenLayers 主地图组件
 * 
 * 设计要点：
 * - 全屏布局，自动适配容器尺寸
 * - 使用 OSM 作为底图
 * - 数据层使用 VectorLayer 渲染城市和路线
 */
export function OpenLayersMap({
  className = '',
  showControls = true,
  onLocationClick
}: OpenLayersMapProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<Map | null>(null);
  const vectorSourceRef = useRef<VectorSource>(new VectorSource());

  const [isMapReady, setIsMapReady] = useState(false);

  // Store hooks
  const { currentAuthor, isLoading: authorLoading } = useAuthorStore();
  const { isPlaying, currentTime } = usePlaybackStore();

  /**
   * 初始化地图实例
   */
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) {
      return;
    }

    console.info('[OpenLayersMap] 初始化地图实例');

    // 创建底图层 - 使用 Stadia Maps Toner 样式
    const tileLayer = new TileLayer({
      source: new StadiaMaps({
        layer: 'stamen_toner',
      }),
      opacity: 0.8
    });

    // 创建数据层
    const vectorLayer = new VectorLayer({
      source: vectorSourceRef.current,
      style: createFeatureStyle
    });

    // 创建地图实例
    const map = new Map({
      target: mapRef.current,
      layers: [tileLayer, vectorLayer],
      view: new View({
        center: fromLonLat([104, 35]), // 中国中心坐标
        zoom: 4,
        minZoom: 3,
        maxZoom: 18
      }),
      controls: showControls ? defaultControls() : []
    });

    mapInstanceRef.current = map;
    setIsMapReady(true);

    console.info('[OpenLayersMap] 地图初始化完成');

    // 清理函数
    return () => {
      console.info('[OpenLayersMap] 销毁地图实例');
      map.setTarget(undefined);
      mapInstanceRef.current = null;
    };
  }, [showControls]);

  /**
   * 更新数据层 - 当作者数据变化时
   */
  useEffect(() => {
    if (!isMapReady || !vectorSourceRef.current) {
      return;
    }

    console.info('[OpenLayersMap] 更新数据层', {
      hasAuthor: !!currentAuthor,
      authorName: currentAuthor?.name
    });

    // 清空现有 Features
    vectorSourceRef.current.clear();

    // 转换并添加新 Features
    if (currentAuthor) {
      const features = convertAuthorToFeatures(currentAuthor);
      vectorSourceRef.current.addFeatures(features);

      console.info('[OpenLayersMap] Features 已添加', {
        count: features.length
      });

      // 自动缩放到数据范围
      if (features.length > 0 && mapInstanceRef.current) {
        const extent = vectorSourceRef.current.getExtent();
        mapInstanceRef.current.getView().fit(extent, {
          padding: [50, 50, 50, 50],
          duration: 1000,
          maxZoom: 6
        });
      }
    }
  }, [currentAuthor, isMapReady]);

  /**
   * 处理地图点击事件
   */
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !onLocationClick) {
      return;
    }

    const handleClick = (event: any) => {
      const features = map.getFeaturesAtPixel(event.pixel);
      
      if (features && features.length > 0) {
        const feature = features[0];
        
        if (feature && 'get' in feature && isCityFeature(feature as any)) {
          const cityName = feature.get('name');
          const coordinates = feature.get('coordinates');
          
          console.info('[OpenLayersMap] 城市点击', { cityName });
          
          onLocationClick({
            type: 'city',
            name: cityName,
            coordinates
          });
        }
      }
    };

    map.on('click', handleClick);

    return () => {
      map.un('click', handleClick);
    };
  }, [isMapReady, onLocationClick]);

  // 渲染加载状态
  if (authorLoading) {
    return (
      <div className={`flex items-center justify-center h-screen bg-gray-900 ${className}`}>
        <div className="text-white text-lg">加载数据中...</div>
      </div>
    );
  }

  return (
    <div
      ref={mapRef}
      className={`absolute inset-0 ${className}`}
      style={{ backgroundColor: '#0a0e1a' }}
    />
  );
}

/**
 * 创建 Feature 样式
 * 根据 Feature 类型（城市/路线）返回不同样式
 */
function createFeatureStyle(feature: FeatureLike): Style {
  if (!feature || !('get' in feature)) {
    return new Style();
  }

  if (isCityFeature(feature as any)) {
    // 城市节点样式
    const routeCount = feature.get('routeCount') || 1;
    const radius = Math.min(6 + routeCount * 2, 16); // 根据路线数量调整大小

    return new Style({
      image: new Circle({
        radius,
        fill: new Fill({ color: '#60a5fa' }),
        stroke: new Stroke({
          color: '#1e40af',
          width: 2
        })
      })
    });
  }

  if (isRouteFeature(feature as any)) {
    // 路线样式
    return new Style({
      stroke: new Stroke({
        color: 'rgba(96, 165, 250, 0.4)',
        width: 2
      })
    });
  }

  // 默认样式
  return new Style({
    stroke: new Stroke({
      color: '#ffffff',
      width: 1
    })
  });
}

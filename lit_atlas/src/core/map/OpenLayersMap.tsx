/**
 * OpenLayers 地图组件 - 全屏交互式地图
 * v0.4.0: 集成墨迹动画系统
 * 
 * 功能：
 * - 全屏地图渲染（非局限在小窗框）
 * - 基于作品出版城市坐标的数据可视化
 * - 墨迹生长、涟漪扩散、路径流动动画
 * - 支持缩放、平移等交互
 * - 集成播放控制和动画效果
 */

import React, { useRef, useEffect, useState } from 'react';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorSource from 'ol/source/Vector';
import OSM from 'ol/source/OSM';
import { fromLonLat } from 'ol/proj';
import { defaults as defaultControls } from 'ol/control';
import { easeOut } from 'ol/easing';

import { useAuthorStore } from '../state/authorStore';
import { convertAuthorToFeatures, isCityFeature } from './utils/featureConverter';
import { AnimationController } from './animation/AnimationController';
import { createInkLayer } from './layers/InkLayer';

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
  const animationControllerRef = useRef<AnimationController | null>(null);

  const [isMapReady, setIsMapReady] = useState(false);

  // Store hooks
  const { currentAuthor, isLoading: authorLoading } = useAuthorStore();

  /**
   * 初始化地图实例
   */
  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) {
      return;
    }

    console.info('[OpenLayersMap] 初始化地图实例（v0.4.0 墨迹动画版）');

    // 创建动画控制器
    const animationController = new AnimationController({
      growthDuration: 2000,
      rippleDuration: 1500,
      flowSpeed: 0.5
    });
    animationControllerRef.current = animationController;

    // 创建底图层 - 使用 OSM 底图（无需授权）
    const tileLayer = new TileLayer({
      source: new OSM({
        crossOrigin: 'anonymous'
      }),
      opacity: 0.8
    });

    // 创建墨迹渲染层（替代标准 VectorLayer）
    const inkLayer = createInkLayer(vectorSourceRef.current, {
      animationController,
      enableAnimation: true
    });

    // 创建地图实例
    const map = new Map({
      target: mapRef.current,
      layers: [tileLayer, inkLayer],
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

    console.info('[OpenLayersMap] 地图初始化完成（墨迹层已激活）');

    // 清理函数
    return () => {
      console.info('[OpenLayersMap] 销毁地图实例');
      animationController.destroy();
      map.setTarget(undefined);
      mapInstanceRef.current = null;
      animationControllerRef.current = null;
    };
  }, [showControls]);

  /**
   * 更新数据层 - 当作者数据变化时
   */
  useEffect(() => {
    if (!isMapReady || !vectorSourceRef.current || !animationControllerRef.current) {
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
      animationControllerRef.current.resetTimeline();

      // 注册动画元数据
      features.forEach((feature, index) => {
        const startTime = index * 500; // 错开动画时间
        const duration = 2000;
        animationControllerRef.current!.registerFeature(feature, startTime, duration);
      });

      vectorSourceRef.current.addFeatures(features);

      console.info('[OpenLayersMap] Features 已添加（动画已注册）', {
        count: features.length
      });

      // 智能聚焦 - 平滑移动到数据范围
      if (features.length > 0 && mapInstanceRef.current) {
        const extent = vectorSourceRef.current.getExtent();
        mapInstanceRef.current.getView().fit(extent, {
          padding: [80, 80, 80, 80],
          duration: 1500,
          easing: easeOut,
          maxZoom: 6
        });
      }
    }
  }, [currentAuthor, isMapReady]);

  /**
   * 注册动画更新回调 - 触发地图重绘
   */
  useEffect(() => {
    const controller = animationControllerRef.current;
    const map = mapInstanceRef.current;
    
    if (!controller || !map) {
      return;
    }

    // 监听动画更新，触发地图重绘
    const unsubscribe = controller.onUpdate(() => {
      map.render(); // 强制重绘地图
    });

    return unsubscribe;
  }, [isMapReady]);

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
      style={{ backgroundColor: '#1a1a1a' }} // 纸张暗色背景
    />
  );
}

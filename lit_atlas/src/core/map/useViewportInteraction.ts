import { useEffect, useRef, useCallback, useState } from 'react';
import { usePlaybackStore, MapInteractionMode } from '../state/playbackStore';

/**
 * 交互模式枚举（已废弃，使用 MapInteractionMode）
 * @deprecated 使用 MapInteractionMode 代替
 */
export enum InteractionMode {
  AUTO = 'auto',
  MANUAL = 'manual'
}

/**
 * 视口交互事件类型
 */
export interface ViewportEvent {
  type: 'zoom' | 'pan' | 'rotate' | 'click';
  data: {
    delta?: { x: number; y: number };
    scale?: number;
    center?: { x: number; y: number };
    coordinates?: [number, number];
  };
  timestamp: number;
}

/**
 * 视口交互配置
 */
export interface ViewportInteractionConfig {
  enableZoom: boolean;
  enablePan: boolean;
  enableRotate: boolean;
  zoomSpeed: number;
  panSpeed: number;
  rotateSpeed: number;
  minZoom: number;
  maxZoom: number;
  bounds?: {
    west: number;
    east: number;
    south: number;
    north: number;
  };
}

/**
 * 默认交互配置
 */
export const DEFAULT_INTERACTION_CONFIG: ViewportInteractionConfig = {
  enableZoom: true,
  enablePan: true,
  enableRotate: false,
  zoomSpeed: 0.1,
  panSpeed: 1,
  rotateSpeed: 0.005,
  minZoom: 0.5,
  maxZoom: 10
};

/**
 * 视口交互Hook返回值
 */
export interface UseViewportInteractionReturn {
  isInteractionEnabled: boolean;
  isDragging: boolean;
  lastEvent: ViewportEvent | null;
  currentMode: MapInteractionMode;
  enableInteraction: () => void;
  disableInteraction: () => void;
  toggleInteraction: () => void;
  handleWheel: (event: WheelEvent) => void;
  handleMouseDown: (event: MouseEvent) => void;
  handleMouseMove: (event: MouseEvent) => void;
  handleMouseUp: (event: MouseEvent) => void;
  handleClick: (event: MouseEvent) => void;
}

/**
 * 视口交互Hook
 * @param containerRef 容器DOM引用
 * @param config 交互配置
 * @returns 交互处理函数和状态
 */
export function useViewportInteraction(
  containerRef: React.RefObject<HTMLElement | null>,
  config: ViewportInteractionConfig = DEFAULT_INTERACTION_CONFIG
): UseViewportInteractionReturn {
  const playbackStore = usePlaybackStore();
  const mapInteractionMode = usePlaybackStore((state) => state.mapInteractionMode);
  const isMapInteractionLocked = usePlaybackStore((state) => state.isMapInteractionLocked);
  
  // 状态管理
  const [isDragging, setIsDragging] = useState(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });
  const lastEventRef = useRef<ViewportEvent | null>(null);
  
  /**
   * 检查交互是否启用
   */
  const isInteractionEnabled = mapInteractionMode === MapInteractionMode.MANUAL && 
    !isMapInteractionLocked &&
    (config.enableZoom || config.enablePan || config.enableRotate);
  
  /**
   * 启用交互模式
   */
  const enableInteraction = useCallback(() => {
    playbackStore.pause(); // 暂停播放
    playbackStore.unlockMapInteraction(); // 解锁地图交互
    console.info('启用手动交互模式');
  }, [playbackStore]);
  
  /**
   * 禁用交互模式
   */
  const disableInteraction = useCallback(() => {
    playbackStore.lockMapInteraction(); // 锁定地图交互
    console.info('禁用手动交互模式');
  }, [playbackStore]);
  
  /**
   * 切换交互模式
   */
  const toggleInteraction = useCallback(() => {
    if (isInteractionEnabled) {
      disableInteraction();
    } else {
      enableInteraction();
    }
  }, [isInteractionEnabled, enableInteraction, disableInteraction]);
  
  /**
   * 处理鼠标滚轮事件（缩放）
   */
  const handleWheel = useCallback((event: WheelEvent) => {
    if (!isInteractionEnabled || !config.enableZoom) {
      event.preventDefault(); // 在锁定模式下阻止默认行为
      return;
    }
    
    event.preventDefault();
    
    const delta = event.deltaY;
    const scale = Math.exp(-delta * config.zoomSpeed * 0.01);
    
    const viewportEvent: ViewportEvent = {
      type: 'zoom',
      data: {
        scale,
        center: { x: event.clientX, y: event.clientY }
      },
      timestamp: Date.now()
    };
    
    lastEventRef.current = viewportEvent;
    console.debug('缩放事件:', viewportEvent);
  }, [isInteractionEnabled, config.enableZoom, config.zoomSpeed]);
  
  /**
   * 处理鼠标按下事件
   */
  const handleMouseDown = useCallback((event: MouseEvent) => {
    if (!isInteractionEnabled || !config.enablePan) {
      return;
    }
    
    event.preventDefault();
    
    setIsDragging(true);
    lastMousePosRef.current = { x: event.clientX, y: event.clientY };
    
    const viewportEvent: ViewportEvent = {
      type: 'pan',
      data: {
        center: { x: event.clientX, y: event.clientY }
      },
      timestamp: Date.now()
    };
    
    lastEventRef.current = viewportEvent;
    console.debug('开始拖拽:', viewportEvent);
  }, [isInteractionEnabled, config.enablePan]);
  
  /**
   * 处理鼠标移动事件
   */
  const handleMouseMove = useCallback((event: MouseEvent) => {
    if (!isInteractionEnabled || !isDragging || !config.enablePan) {
      return;
    }
    
    event.preventDefault();
    
    const delta = {
      x: event.clientX - lastMousePosRef.current.x,
      y: event.clientY - lastMousePosRef.current.y
    };
    
    lastMousePosRef.current = { x: event.clientX, y: event.clientY };
    
    const viewportEvent: ViewportEvent = {
      type: 'pan',
      data: { delta },
      timestamp: Date.now()
    };
    
    lastEventRef.current = viewportEvent;
  }, [isInteractionEnabled, isDragging, config.enablePan]);
  
  /**
   * 处理鼠标释放事件
   */
  const handleMouseUp = useCallback((event: MouseEvent) => {
    if (isDragging) {
      setIsDragging(false);
      console.debug('结束拖拽');
    }
  }, [isDragging]);
  
  /**
   * 处理点击事件
   */
  const handleClick = useCallback((event: MouseEvent) => {
    if (!isInteractionEnabled) {
      // 在锁定模式下，点击启用手动模式
      enableInteraction();
      return;
    }
    
    const viewportEvent: ViewportEvent = {
      type: 'click',
      data: {
        center: { x: event.clientX, y: event.clientY }
      },
      timestamp: Date.now()
    };
    
    lastEventRef.current = viewportEvent;
    console.debug('点击事件:', viewportEvent);
  }, [isInteractionEnabled, enableInteraction]);
  
  // 事件监听器设置
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    
    // 在锁定模式下阻止所有交互
    if (!isInteractionEnabled) {
      const preventDefault = (event: Event) => event.preventDefault();
      container.addEventListener('wheel', preventDefault, { passive: false });
      container.addEventListener('mousedown', preventDefault, { passive: false });
      container.addEventListener('touchstart', preventDefault, { passive: false });
      
      return () => {
        container.removeEventListener('wheel', preventDefault);
        container.removeEventListener('mousedown', preventDefault);
        container.removeEventListener('touchstart', preventDefault);
      };
    }
    
    // 在手动模式下添加事件监听
    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('mousedown', handleMouseDown);
    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseup', handleMouseUp);
    container.addEventListener('click', handleClick);
    
    // 清理事件监听器
    return () => {
      container.removeEventListener('wheel', handleWheel);
      container.removeEventListener('mousedown', handleMouseDown);
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseup', handleMouseUp);
      container.removeEventListener('click', handleClick);
    };
  }, [
    containerRef,
    isInteractionEnabled,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleClick
  ]);
  
  return {
    isInteractionEnabled,
    isDragging,
    lastEvent: lastEventRef.current,
    currentMode: mapInteractionMode,
    enableInteraction,
    disableInteraction,
    toggleInteraction,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleClick
  };
}
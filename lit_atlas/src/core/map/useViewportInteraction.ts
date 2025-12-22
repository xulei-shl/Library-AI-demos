import { useEffect, useRef, useCallback } from 'react';
import { usePlaybackStore } from '../state/playbackStore';

/**
 * 交互模式枚举
 */
export enum InteractionMode {
  AUTO = 'auto',   // 自动播放模式，锁定用户输入
  MANUAL = 'manual' // 手动模式，允许用户交互
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
  mode: InteractionMode;
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
  mode: InteractionMode.AUTO,
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
  enableInteraction: () => void;
  disableInteraction: () => void;
  setMode: (mode: InteractionMode) => void;
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
  
  // 状态管理
  const isDraggingRef = useRef(false);
  const lastMousePosRef = useRef({ x: 0, y: 0 });
  const lastEventRef = useRef<ViewportEvent | null>(null);
  
  /**
   * 检查交互是否启用
   */
  const isInteractionEnabled = config.mode === InteractionMode.MANUAL && 
    (config.enableZoom || config.enablePan || config.enableRotate);
  
  /**
   * 启用交互模式
   */
  const enableInteraction = useCallback(() => {
    playbackStore.pause(); // 自动播放时暂停
    console.info('启用手动交互模式');
  }, [playbackStore]);
  
  /**
   * 禁用交互模式
   */
  const disableInteraction = useCallback(() => {
    console.info('禁用手动交互模式');
  }, []);
  
  /**
   * 设置交互模式
   */
  const setMode = useCallback((mode: InteractionMode) => {
    if (mode === InteractionMode.MANUAL) {
      enableInteraction();
    } else {
      disableInteraction();
    }
  }, [enableInteraction, disableInteraction]);
  
  /**
   * 处理鼠标滚轮事件（缩放）
   */
  const handleWheel = useCallback((event: WheelEvent) => {
    if (!isInteractionEnabled || !config.enableZoom) {
      return; // 在自动模式下阻止默认行为
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
    
    isDraggingRef.current = true;
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
    if (!isInteractionEnabled || !isDraggingRef.current || !config.enablePan) {
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
  }, [isInteractionEnabled, config.enablePan]);
  
  /**
   * 处理鼠标释放事件
   */
  const handleMouseUp = useCallback((event: MouseEvent) => {
    if (!isInteractionEnabled) {
      return;
    }
    
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
      console.debug('结束拖拽');
    }
  }, [isInteractionEnabled]);
  
  /**
   * 处理点击事件
   */
  const handleClick = useCallback((event: MouseEvent) => {
    if (!isInteractionEnabled) {
      // 在自动模式下，点击启用手动模式
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
    
    // 在自动模式下阻止所有交互
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
  
  // 监听播放状态变化，自动切换交互模式
  useEffect(() => {
    const unsubscribe = usePlaybackStore.subscribe(
      (state) => state.isPlaying,
      (isPlaying) => {
        if (isPlaying && config.mode === InteractionMode.AUTO) {
          // 自动播放时锁定交互
          disableInteraction();
        } else if (!isPlaying && config.mode === InteractionMode.AUTO) {
          // 暂停时可以启用交互
          console.debug('播放暂停，允许用户交互');
        }
      }
    );
    
    return unsubscribe;
  }, [config.mode, disableInteraction]);
  
  return {
    isInteractionEnabled,
    isDragging: isDraggingRef.current,
    lastEvent: lastEventRef.current,
    enableInteraction,
    disableInteraction,
    setMode,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleClick
  };
}
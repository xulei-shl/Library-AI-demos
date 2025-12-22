import * as d3 from 'd3';
import { BoundingBox } from '../../utils/geo/coordinateUtils';

/**
 * 相机参数接口
 */
export interface CameraParams {
  center: [number, number]; // [longitude, latitude]
  zoom: number;
  rotation: [number, number, number]; // [lambda, phi, gamma] in degrees
}

/**
 * 飞行动画参数
 */
export interface FlyToParams {
  center: [number, number];
  zoom: number;
  rotation?: [number, number, number];
  duration: number;
  easing?: (t: number) => number;
}

/**
 * 相机状态
 */
export interface CameraState extends CameraParams {
  width: number;
  height: number;
  padding: number;
}

/**
 * 作者边界盒
 */
export interface AuthorBBox extends BoundingBox {
  works: Array<{
    id: string;
    title: string;
    routes: Array<{
      start: [number, number]; // [lng, lat]
      end: [number, number];   // [lng, lat]
    }>;
  }>;
}

/**
 * 相机控制器类
 */
export class CameraController {
  private projection: d3.GeoProjection;
  private currentState: CameraState;
  
  constructor(width: number, height: number, padding: number = 50) {
    this.projection = d3.geoMercator();
    this.currentState = {
      center: [105, 35], // 默认中国中心
      zoom: 1,
      rotation: [0, 0, 0],
      width,
      height,
      padding
    };
    
    this.updateProjection();
  }
  
  /**
   * 更新投影配置
   */
  private updateProjection(): void {
    this.projection
      .scale(this.currentState.zoom * 150)
      .center(this.currentState.center)
      .rotate(this.currentState.rotation)
      .translate([this.currentState.width / 2, this.currentState.height / 2]);
  }
  
  /**
   * 计算适配作者数据的边界盒
   * @param authorBBox 作者边界盒数据
   * @returns 优化后的边界盒
   */
  calculateAuthorBBox(authorBBox: AuthorBBox): BoundingBox {
    const { west, east, south, north, works } = authorBBox;
    
    // 收集所有坐标点
    const coordinates: [number, number][] = [];
    
    // 添加边界点
    coordinates.push(
      [west, south],
      [east, south],
      [east, north],
      [west, north],
      [west, south] // 闭合边界
    );
    
    // 添加所有作品的路线点
    works.forEach(work => {
      work.routes.forEach(route => {
        coordinates.push(route.start, route.end);
      });
    });
    
    // 计算实际边界
    const lons = coordinates.map(coord => coord[0]);
    const lats = coordinates.map(coord => coord[1]);
    
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    
    // 添加缓冲区域
    const lonPadding = (maxLon - minLon) * 0.1;
    const latPadding = (maxLat - minLat) * 0.1;
    
    return {
      west: minLon - lonPadding,
      east: maxLon + lonPadding,
      south: minLat - latPadding,
      north: maxLat + latPadding
    };
  }
  
  /**
   * 计算Smart FlyTo参数
   * @param bbox 边界盒
   * @param paddingPct 内边距百分比
   * @param duration 动画持续时间
   * @returns 飞行动画参数
   */
  calculateSmartFlyTo(
    bbox: BoundingBox,
    paddingPct: number = 0.1,
    duration: number = 1000
  ): FlyToParams {
    const { west, east, south, north } = bbox;
    
    // 计算中心点
    const centerLon = (west + east) / 2;
    const centerLat = (south + north) / 2;
    
    // 计算尺寸
    const bboxWidth = east - west;
    const bboxHeight = north - south;
    
    // 计算适配的缩放级别
    const availableWidth = this.currentState.width * (1 - paddingPct * 2);
    const availableHeight = this.currentState.height * (1 - paddingPct * 2);
    
    const scaleX = availableWidth / bboxWidth;
    const scaleY = availableHeight / bboxHeight;
    
    // 选择较小的缩放比例以确保完全显示
    const zoomScale = Math.min(scaleX, scaleY);
    
    // 计算最终的缩放级别
    const zoom = Math.max(1, zoomScale / 150);
    
    // 应用边界约束
    const constrainedZoom = Math.min(zoom, 10); // 最大缩放级别
    const minZoom = 0.5; // 最小缩放级别
    const finalZoom = Math.max(minZoom, constrainedZoom);
    
    console.info('Smart FlyTo 参数计算:', {
      bbox: `${west.toFixed(2)}, ${south.toFixed(2)} - ${east.toFixed(2)}, ${north.toFixed(2)}`,
      center: [centerLon.toFixed(2), centerLat.toFixed(2)],
      zoom: finalZoom.toFixed(2),
      duration
    });
    
    return {
      center: [centerLon, centerLat],
      zoom: finalZoom,
      duration,
      easing: d3.easeCubicInOut
    };
  }
  
  /**
   * 执行飞行动画
   * @param params 飞行动画参数
   * @param onUpdate 更新回调
   * @returns Promise
   */
  async flyTo(
    params: FlyToParams,
    onUpdate?: (state: CameraState) => void
  ): Promise<void> {
    const startState = { ...this.currentState };
    const { center, zoom, rotation = [0, 0, 0], duration, easing = d3.easeCubicInOut } = params;
    
    return new Promise((resolve) => {
      const startTime = Date.now();
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const t = easing(progress);
        
        // 插值计算当前状态
        const currentCenter: [number, number] = [
          startState.center[0] + (center[0] - startState.center[0]) * t,
          startState.center[1] + (center[1] - startState.center[1]) * t
        ];
        
        const currentZoom = startState.zoom + (zoom - startState.zoom) * t;
        
        const currentRotation: [number, number, number] = [
          startState.rotation[0] + (rotation[0] - startState.rotation[0]) * t,
          startState.rotation[1] + (rotation[1] - startState.rotation[1]) * t,
          startState.rotation[2] + (rotation[2] - startState.rotation[2]) * t
        ];
        
        // 更新当前状态
        this.currentState = {
          ...this.currentState,
          center: currentCenter,
          zoom: currentZoom,
          rotation: currentRotation
        };
        
        this.updateProjection();
        
        // 触发更新回调
        if (onUpdate) {
          onUpdate(this.currentState);
        }
        
        // 继续动画或完成
        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          console.info('飞行动画完成');
          resolve();
        }
      };
      
      animate();
    });
  }
  
  /**
   * 缩放到指定级别
   * @param zoom 缩放级别
   * @param duration 动画持续时间
   */
  async zoomTo(zoom: number, duration: number = 500): Promise<void> {
    const params: FlyToParams = {
      center: this.currentState.center,
      zoom: Math.max(0.5, Math.min(10, zoom)),
      duration
    };
    
    await this.flyTo(params);
  }
  
  /**
   * 平移到指定中心点
   * @param center 中心点坐标
   * @param duration 动画持续时间
   */
  async panTo(center: [number, number], duration: number = 500): Promise<void> {
    const params: FlyToParams = {
      center,
      zoom: this.currentState.zoom,
      duration
    };
    
    await this.flyTo(params);
  }
  
  /**
   * 重置到默认视角
   * @param duration 动画持续时间
   */
  async reset(duration: number = 1000): Promise<void> {
    const params: FlyToParams = {
      center: [105, 35], // 中国中心
      zoom: 1,
      duration
    };
    
    await this.flyTo(params);
  }
  
  /**
   * 获取当前相机状态
   */
  getState(): CameraState {
    return { ...this.currentState };
  }
  
  /**
   * 设置画布尺寸
   * @param width 宽度
   * @param height 高度
   */
  setSize(width: number, height: number): void {
    this.currentState.width = width;
    this.currentState.height = height;
    this.updateProjection();
  }
  
  /**
   * 获取投影对象
   */
  getProjection(): d3.GeoProjection {
    return this.projection;
  }
  
  /**
   * 将地理坐标转换为屏幕坐标
   * @param coordinates 地理坐标 [lng, lat]
   * @returns 屏幕坐标 [x, y]
   */
  project(coordinates: [number, number]): [number, number] {
    return this.projection(coordinates) as [number, number];
  }
  
  /**
   * 将屏幕坐标转换为地理坐标
   * @param screen 屏幕坐标 [x, y]
   * @returns 地理坐标 [lng, lat]
   */
  unproject(screen: [number, number]): [number, number] | null {
    const result = this.projection.invert?.(screen);
    return result ? (result as [number, number]) : null;
  }
}
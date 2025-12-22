/**
 * 时间轴构建器
 * 根据路线数据计算事件时间和持续时间
 * 参考：@docs/design/narrative_scheduler_20251215.md
 */

import { Route } from '../data/normalizers';
import { calculateDistance } from '../../utils/geo/coordinateUtils';
import {
  TimelineConfig,
  DEFAULT_TIMELINE_CONFIG,
  SchedulerEvent,
  SchedulerEventType,
  LineStartEvent,
  LineCompleteEvent,
  RippleTriggerEvent,
} from './types';

/**
 * 时间轴构建器类
 */
export class TimelineBuilder {
  private config: TimelineConfig;

  constructor(config: Partial<TimelineConfig> = {}) {
    this.config = { ...DEFAULT_TIMELINE_CONFIG, ...config };
  }

  /**
   * 根据路线构建完整的事件时间轴
   * @param routes 路线数组
   * @param authorColor 作者主题色
   * @returns 排序后的事件数组
   */
  buildTimeline(routes: Route[], authorColor: string = '#2c3e50'): SchedulerEvent[] {
    const events: SchedulerEvent[] = [];
    let currentTime = 0;

    // 按年份排序路线
    const sortedRoutes = this.sortRoutesByYear(routes);

    sortedRoutes.forEach((route, index) => {
      // 计算线条持续时间
      const duration = this.calculateRouteDuration(route);
      
      // 生成线条开始事件
      const lineStartEvent = this.createLineStartEvent(
        route,
        currentTime,
        duration,
        authorColor
      );
      events.push(lineStartEvent);

      // 生成线条完成事件
      const lineCompleteTime = currentTime + duration;
      const lineCompleteEvent = this.createLineCompleteEvent(
        route,
        lineCompleteTime
      );
      events.push(lineCompleteEvent);

      // 生成涟漪触发事件（在线条完成后）
      const rippleTime = lineCompleteTime + this.config.rippleDelay;
      const rippleEvent = this.createRippleTriggerEvent(
        route,
        rippleTime
      );
      events.push(rippleEvent);

      // 更新当前时间（加上最小间隔）
      currentTime = rippleTime + this.config.rippleDuration + this.config.minInterval;
    });

    console.info(`时间轴构建完成: ${events.length} 个事件, 总时长 ${currentTime}ms`);
    
    return events;
  }

  /**
   * 按年份排序路线
   */
  private sortRoutesByYear(routes: Route[]): Route[] {
    return [...routes].sort((a, b) => {
      const yearA = a.year || 0;
      const yearB = b.year || 0;
      return yearA - yearB;
    });
  }

  /**
   * 计算路线持续时间
   */
  private calculateRouteDuration(route: Route): number {
    // 计算地理距离
    const distance = calculateDistance(
      route.start_location.coordinates,
      route.end_location.coordinates
    );

    // 基础时长 + 距离因子
    const distanceBonus = (distance / 1000) * this.config.distanceFactor * 1000;
    
    // 年份因子（可选）
    const yearFactor = this.config.yearFactor;
    
    const duration = (this.config.baseDuration + distanceBonus) * yearFactor;
    
    // 确保最小持续时间
    return Math.max(duration, 500);
  }

  /**
   * 创建线条开始事件
   */
  private createLineStartEvent(
    route: Route,
    timestamp: number,
    duration: number,
    color: string
  ): LineStartEvent {
    return {
      id: `line-start-${route.id}`,
      type: SchedulerEventType.LINE_START,
      timestamp,
      duration,
      routeId: route.id,
      route,
      coordinates: [
        [route.start_location.coordinates.lng, route.start_location.coordinates.lat],
        [route.end_location.coordinates.lng, route.end_location.coordinates.lat],
      ],
      color,
      year: route.year,
    };
  }

  /**
   * 创建线条完成事件
   */
  private createLineCompleteEvent(
    route: Route,
    timestamp: number
  ): LineCompleteEvent {
    return {
      id: `line-complete-${route.id}`,
      type: SchedulerEventType.LINE_COMPLETE,
      timestamp,
      duration: 0,
      routeId: route.id,
    };
  }

  /**
   * 创建涟漪触发事件
   */
  private createRippleTriggerEvent(
    route: Route,
    timestamp: number
  ): RippleTriggerEvent {
    const endLocation = route.end_location;
    const collectionInfo = route.collection_info;

    return {
      id: `ripple-${route.id}`,
      type: SchedulerEventType.RIPPLE_TRIGGER,
      timestamp,
      duration: this.config.rippleDuration,
      cityId: endLocation.name,
      cityName: endLocation.name,
      coordinates: [endLocation.coordinates.lng, endLocation.coordinates.lat],
      routeId: route.id,
      hasCollection: collectionInfo?.has_collection || false,
      collectionMeta: collectionInfo?.collection_meta as { title: string; date: string; location: string } | undefined,
      year: route.year,
    };
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<TimelineConfig>): void {
    this.config = { ...this.config, ...config };
    console.info('时间轴配置已更新', this.config);
  }

  /**
   * 获取当前配置
   */
  getConfig(): TimelineConfig {
    return { ...this.config };
  }
}

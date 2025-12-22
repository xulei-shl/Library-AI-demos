/**
 * 事件总线 - 基于 RxJS
 * 参考：@docs/design/data_orchestrator_20251215.md
 */

import { Subject, Observable } from 'rxjs';
import { filter, map } from 'rxjs/operators';

/**
 * 事件类型定义
 */
export enum EventType {
  // 播放控制事件
  PLAYBACK_PLAY = 'playback:play',
  PLAYBACK_PAUSE = 'playback:pause',
  PLAYBACK_SEEK = 'playback:seek',
  PLAYBACK_RESET = 'playback:reset',

  // 叙事调度事件
  LINE_START = 'narrative:line_start',
  LINE_PROGRESS = 'narrative:line_progress',
  LINE_COMPLETE = 'narrative:line_complete',
  RIPPLE_TRIGGER = 'narrative:ripple_trigger',

  // 地图交互事件
  MAP_ZOOM = 'map:zoom',
  MAP_PAN = 'map:pan',
  MAP_FLYTO = 'map:flyto',
  MAP_INTERACTION_START = 'map:interaction_start',
  MAP_INTERACTION_END = 'map:interaction_end',

  // 数据加载事件
  DATA_LOAD_START = 'data:load_start',
  DATA_LOAD_SUCCESS = 'data:load_success',
  DATA_LOAD_ERROR = 'data:load_error',

  // 作者切换事件
  AUTHOR_CHANGE = 'author:change',
}

/**
 * 事件数据接口
 */
export interface AppEvent<T = unknown> {
  type: EventType;
  payload: T;
  timestamp: number;
}

/**
 * 全局事件总线
 */
class EventBus {
  private subject = new Subject<AppEvent>();

  /**
   * 发布事件
   */
  emit<T = unknown>(type: EventType, payload?: T): void {
    this.subject.next({
      type,
      payload,
      timestamp: Date.now(),
    });
  }

  /**
   * 订阅特定类型的事件
   */
  on<T = unknown>(type: EventType): Observable<T> {
    return this.subject.pipe(
      filter((event) => event.type === type),
      map((event) => event.payload as T),
    ) as Observable<T>;
  }

  /**
   * 订阅所有事件
   */
  onAll(): Observable<AppEvent> {
    return this.subject.asObservable();
  }

  /**
   * 清空所有订阅（用于测试）
   */
  clear(): void {
    this.subject.complete();
  }
}

/**
 * 全局单例
 */
export const eventBus = new EventBus();

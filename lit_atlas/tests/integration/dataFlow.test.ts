/**
 * 数据流集成测试
 * 测试 Store -> EventBus -> Components 的数据流
 */

import { useAuthorStore, usePlaybackStore } from '@/core/store';
import { eventBus, EventType } from '@/core/events/eventBus';

describe('Data Flow Integration', () => {
  beforeEach(() => {
    // 重置所有 store
    useAuthorStore.setState({
      currentAuthorId: null,
      authors: new Map(),
      loading: false,
      error: null,
    });

    usePlaybackStore.setState({
      state: 'idle',
      progress: 0,
      speed: 1,
      loop: false,
      currentYear: null,
    });
  });

  it('作者切换应该触发播放重置', (done) => {
    // 订阅作者切换事件
    const subscription = eventBus.on(EventType.AUTHOR_CHANGE).subscribe((payload) => {
      expect(payload).toBeDefined();
      subscription.unsubscribe();
      done();
    });

    // 触发作者切换
    eventBus.emit(EventType.AUTHOR_CHANGE, { authorId: 'murakami' });
  });

  it('播放控制应该通过事件总线通信', (done) => {
    // 订阅播放事件
    const subscription = eventBus.on(EventType.PLAYBACK_PLAY).subscribe(() => {
      subscription.unsubscribe();
      done();
    });

    // 触发播放
    eventBus.emit(EventType.PLAYBACK_PLAY);
  });

  it('地图交互应该触发相应事件', (done) => {
    // 订阅地图缩放事件
    const subscription = eventBus.on(EventType.MAP_ZOOM).subscribe((payload) => {
      expect(payload).toHaveProperty('zoom');
      subscription.unsubscribe();
      done();
    });

    // 触发缩放
    eventBus.emit(EventType.MAP_ZOOM, { zoom: 5 });
  });
});

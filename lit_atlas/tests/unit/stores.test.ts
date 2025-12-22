/**
 * Store 单元测试
 * 参考：@docs/design/data_orchestrator_20251215.md
 */

import { useAuthorStore, usePlaybackStore } from '@/core/store';

describe('Author Store', () => {
  beforeEach(() => {
    // 重置 store 状态
    useAuthorStore.setState({
      currentAuthorId: null,
      authors: new Map(),
      loading: false,
      error: null,
    });
  });

  it('应该初始化为空状态', () => {
    const state = useAuthorStore.getState();
    expect(state.currentAuthorId).toBeNull();
    expect(state.authors.size).toBe(0);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it('应该能够设置当前作者', () => {
    const { setCurrentAuthor } = useAuthorStore.getState();
    setCurrentAuthor('murakami');

    const state = useAuthorStore.getState();
    expect(state.currentAuthorId).toBe('murakami');
    expect(state.error).toBeNull();
  });

  it('应该能够添加作者元数据', () => {
    const { addAuthor } = useAuthorStore.getState();
    addAuthor({
      id: 'murakami',
      name: 'Haruki Murakami',
      name_zh: '村上春树',
      theme_color: '#2C3E50',
    });

    const state = useAuthorStore.getState();
    expect(state.authors.size).toBe(1);
    expect(state.authors.get('murakami')?.name_zh).toBe('村上春树');
  });

  it('应该能够清除当前作者', () => {
    const { setCurrentAuthor, clearCurrentAuthor } = useAuthorStore.getState();
    setCurrentAuthor('murakami');
    clearCurrentAuthor();

    const state = useAuthorStore.getState();
    expect(state.currentAuthorId).toBeNull();
  });
});

describe('Playback Store', () => {
  beforeEach(() => {
    // 重置 store 状态
    usePlaybackStore.setState({
      state: 'idle',
      progress: 0,
      speed: 1,
      loop: false,
      currentYear: null,
    });
  });

  it('应该初始化为 idle 状态', () => {
    const state = usePlaybackStore.getState();
    expect(state.state).toBe('idle');
    expect(state.progress).toBe(0);
    expect(state.speed).toBe(1);
  });

  it('应该能够播放', () => {
    const { play } = usePlaybackStore.getState();
    play();

    const state = usePlaybackStore.getState();
    expect(state.state).toBe('playing');
  });

  it('应该能够暂停', () => {
    const { play, pause } = usePlaybackStore.getState();
    play();
    pause();

    const state = usePlaybackStore.getState();
    expect(state.state).toBe('paused');
  });

  it('应该能够跳转进度', () => {
    const { seek } = usePlaybackStore.getState();
    seek(0.5);

    const state = usePlaybackStore.getState();
    expect(state.state).toBe('seeking');
    expect(state.progress).toBe(0.5);
  });

  it('进度应该限制在 0-1 之间', () => {
    const { seek } = usePlaybackStore.getState();
    seek(1.5);

    const state = usePlaybackStore.getState();
    expect(state.progress).toBe(1);

    seek(-0.5);
    const state2 = usePlaybackStore.getState();
    expect(state2.progress).toBe(0);
  });

  it('应该能够设置播放速度', () => {
    const { setSpeed } = usePlaybackStore.getState();
    setSpeed(2);

    const state = usePlaybackStore.getState();
    expect(state.speed).toBe(2);
  });

  it('应该能够重置状态', () => {
    const { play, seek, reset } = usePlaybackStore.getState();
    play();
    seek(0.5);
    reset();

    const state = usePlaybackStore.getState();
    expect(state.state).toBe('idle');
    expect(state.progress).toBe(0);
  });
});

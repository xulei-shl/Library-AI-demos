/**
 * 作者状态管理测试
 * 参考：@docs/design/data_orchestrator_20251215.md
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuthorStore, playbackBus } from '../../../src/core/state/authorStore';
import * as dataLoader from '../../../src/core/data/dataLoader';

// Mock dataLoader
jest.mock('../../../src/core/data/dataLoader');

describe('AuthorStore', () => {
  const mockAuthor = {
    id: 'test_author',
    name: '测试作者',
    birth_year: 1900,
    death_year: 2000,
    biography: '测试传记',
    works: [
      {
        id: 'test_work',
        title: '测试作品',
        year: 1950,
        routes: [
          {
            id: 'test_route',
            start_location: {
              name: '北京',
              coordinates: { lat: 39.9042, lng: 116.4074 }
            },
            end_location: {
              name: '上海',
              coordinates: { lat: 31.2304, lng: 121.4737 }
            },
            year: 1950,
            description: '测试路线',
            collection_info: { has_collection: false }
          }
        ],
        metadata: {
          genre: '测试类型',
          themes: ['测试主题'],
          language: '中文'
        }
      }
    ]
  };

  beforeEach(() => {
    // 重置 store 状态
    const { result } = renderHook(() => useAuthorStore());
    act(() => {
      result.current.clearCache();
    });

    // 重置 mock
    jest.clearAllMocks();
  });

  describe('loadAuthor', () => {
    it('应该成功加载作者', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockResolvedValue(mockAuthor);

      const { result } = renderHook(() => useAuthorStore());

      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      expect(result.current.currentAuthor).toEqual(mockAuthor);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('应该在加载时设置 loading 状态', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockImplementation(
        () => new Promise(resolve => setTimeout(() => resolve(mockAuthor), 100))
      );

      const { result } = renderHook(() => useAuthorStore());

      act(() => {
        result.current.loadAuthor('test_author');
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('应该处理加载错误', async () => {
      const error = new Error('加载失败');
      (dataLoader.loadAuthor as jest.Mock).mockRejectedValue(error);

      const { result } = renderHook(() => useAuthorStore());

      await act(async () => {
        try {
          await result.current.loadAuthor('invalid_author');
        } catch (e) {
          // 预期会抛出错误
        }
      });

      expect(result.current.currentAuthor).toBeNull();
      expect(result.current.error).toBe('加载失败');
      expect(result.current.isLoading).toBe(false);
    });

    it('应该在切换作者时广播事件', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockResolvedValue(mockAuthor);

      const eventSpy = jest.fn();
      const subscription = playbackBus.subscribe(eventSpy);

      const { result } = renderHook(() => useAuthorStore());

      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      expect(eventSpy).toHaveBeenCalled();
      const event = eventSpy.mock.calls[0][0];
      expect(event.type).toBe('STOP');
      expect(event.data?.authorId).toBe('test_author');

      subscription.unsubscribe();
    });

    it('应该跳过重复加载相同作者', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockResolvedValue(mockAuthor);

      const { result } = renderHook(() => useAuthorStore());

      // 第一次加载
      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      expect(dataLoader.loadAuthor).toHaveBeenCalledTimes(1);

      // 第二次加载相同作者
      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      // 不应该再次调用 loadAuthor
      expect(dataLoader.loadAuthor).toHaveBeenCalledTimes(1);
    });
  });

  describe('setCurrentWork', () => {
    it('应该设置当前作品', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockResolvedValue(mockAuthor);

      const { result } = renderHook(() => useAuthorStore());

      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      const work = mockAuthor.works[0];

      act(() => {
        result.current.setCurrentWork(work);
      });

      expect(result.current.currentWork).toEqual(work);
    });

    it('应该在设置作品时广播重置事件', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockResolvedValue(mockAuthor);

      const eventSpy = jest.fn();
      const subscription = playbackBus.subscribe(eventSpy);

      const { result } = renderHook(() => useAuthorStore());

      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      // 清除之前的事件
      eventSpy.mockClear();

      const work = mockAuthor.works[0];

      act(() => {
        result.current.setCurrentWork(work);
      });

      expect(eventSpy).toHaveBeenCalled();
      const event = eventSpy.mock.calls[0][0];
      expect(event.type).toBe('RESET');
      expect(event.data?.workId).toBe(work.id);

      subscription.unsubscribe();
    });
  });

  describe('状态查询', () => {
    it('getCurrentAuthor 应该返回当前作者', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockResolvedValue(mockAuthor);

      const { result } = renderHook(() => useAuthorStore());

      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      const author = result.current.getCurrentAuthor();
      expect(author).toEqual(mockAuthor);
    });

    it('isAuthorLoaded 应该正确判断作者是否已加载', async () => {
      (dataLoader.loadAuthor as jest.Mock).mockResolvedValue(mockAuthor);

      const { result } = renderHook(() => useAuthorStore());

      expect(result.current.isAuthorLoaded('test_author')).toBe(false);

      await act(async () => {
        await result.current.loadAuthor('test_author');
      });

      expect(result.current.isAuthorLoaded('test_author')).toBe(true);
      expect(result.current.isAuthorLoaded('other_author')).toBe(false);
    });
  });

  describe('clearError', () => {
    it('应该清除错误状态', async () => {
      const error = new Error('测试错误');
      (dataLoader.loadAuthor as jest.Mock).mockRejectedValue(error);

      const { result } = renderHook(() => useAuthorStore());

      await act(async () => {
        try {
          await result.current.loadAuthor('invalid_author');
        } catch (e) {
          // 预期错误
        }
      });

      expect(result.current.error).toBeTruthy();

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBeNull();
    });
  });
});

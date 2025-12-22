/**
 * 数据加载器测试
 * 参考：@docs/design/data_orchestrator_20251215.md
 */

import { loadAuthor, clearCache, getCacheStats, DataLoadError } from '../../../src/core/data/dataLoader';
import { Author } from '../../../src/core/data/normalizers';

// Mock fetch API
global.fetch = jest.fn();

describe('DataLoader', () => {
  beforeEach(() => {
    // 清除缓存
    clearCache();
    // 重置 mock
    (global.fetch as jest.Mock).mockReset();
  });

  describe('loadAuthor', () => {
    it('应该成功加载作者数据', async () => {
      // 准备测试数据
      const mockAuthorData = {
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

      // Mock fetch 响应
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockAuthorData
      });

      // 执行加载
      const author = await loadAuthor('test_author');

      // 验证结果
      expect(author).toBeDefined();
      expect(author.id).toBe('test_author');
      expect(author.name).toBe('测试作者');
      expect(author.works).toHaveLength(1);
      expect(author.works[0].routes).toHaveLength(1);

      // 验证 fetch 被调用
      expect(global.fetch).toHaveBeenCalledWith('/data/authors/test_author.json');
    });

    it('应该使用缓存避免重复加载', async () => {
      const mockAuthorData = {
        id: 'cached_author',
        name: '缓存作者',
        birth_year: 1900,
        biography: '测试',
        works: []
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockAuthorData
      });

      // 第一次加载
      const author1 = await loadAuthor('cached_author');
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // 第二次加载应该使用缓存
      const author2 = await loadAuthor('cached_author');
      expect(global.fetch).toHaveBeenCalledTimes(1); // 没有新的请求
      expect(author1).toBe(author2); // 返回相同的对象
    });

    it('应该处理 HTTP 错误', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found'
      });

      await expect(loadAuthor('nonexistent_author')).rejects.toThrow(DataLoadError);
    });

    it('应该处理无效的 JSON 数据', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => null
      });

      await expect(loadAuthor('invalid_author')).rejects.toThrow();
    });

    it('应该验证作者必须有作品', async () => {
      const mockAuthorData = {
        id: 'no_works_author',
        name: '无作品作者',
        birth_year: 1900,
        biography: '测试',
        works: []
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockAuthorData
      });

      await expect(loadAuthor('no_works_author')).rejects.toThrow('没有作品数据');
    });
  });

  describe('缓存管理', () => {
    it('应该正确统计缓存', async () => {
      const mockAuthorData = {
        id: 'author1',
        name: '作者1',
        birth_year: 1900,
        biography: '测试',
        works: [
          {
            id: 'work1',
            title: '作品1',
            routes: [
              {
                id: 'route1',
                start_location: {
                  name: '北京',
                  coordinates: { lat: 39.9042, lng: 116.4074 }
                },
                end_location: {
                  name: '上海',
                  coordinates: { lat: 31.2304, lng: 121.4737 }
                },
                collection_info: { has_collection: false }
              }
            ],
            metadata: {
              genre: '测试',
              themes: [],
              language: '中文'
            }
          }
        ]
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockAuthorData
      });

      // 初始状态
      let stats = getCacheStats();
      expect(stats.cachedAuthors).toBe(0);

      // 加载一个作者
      await loadAuthor('author1');
      stats = getCacheStats();
      expect(stats.cachedAuthors).toBe(1);
      expect(stats.authorIds).toContain('author1');
    });

    it('应该能清除指定作者的缓存', async () => {
      const mockAuthorData = {
        id: 'author_to_clear',
        name: '待清除作者',
        birth_year: 1900,
        biography: '测试',
        works: [
          {
            id: 'work1',
            title: '作品1',
            routes: [
              {
                id: 'route1',
                start_location: {
                  name: '北京',
                  coordinates: { lat: 39.9042, lng: 116.4074 }
                },
                end_location: {
                  name: '上海',
                  coordinates: { lat: 31.2304, lng: 121.4737 }
                },
                collection_info: { has_collection: false }
              }
            ],
            metadata: {
              genre: '测试',
              themes: [],
              language: '中文'
            }
          }
        ]
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockAuthorData
      });

      // 加载作者
      await loadAuthor('author_to_clear');
      expect(getCacheStats().cachedAuthors).toBe(1);

      // 清除缓存
      clearCache('author_to_clear');
      expect(getCacheStats().cachedAuthors).toBe(0);
    });

    it('应该能清除所有缓存', async () => {
      const mockAuthorData = {
        id: 'author',
        name: '作者',
        birth_year: 1900,
        biography: '测试',
        works: [
          {
            id: 'work1',
            title: '作品1',
            routes: [
              {
                id: 'route1',
                start_location: {
                  name: '北京',
                  coordinates: { lat: 39.9042, lng: 116.4074 }
                },
                end_location: {
                  name: '上海',
                  coordinates: { lat: 31.2304, lng: 121.4737 }
                },
                collection_info: { has_collection: false }
              }
            ],
            metadata: {
              genre: '测试',
              themes: [],
              language: '中文'
            }
          }
        ]
      };

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockAuthorData
      });

      // 加载多个作者
      await loadAuthor('author1');
      await loadAuthor('author2');
      expect(getCacheStats().cachedAuthors).toBeGreaterThan(0);

      // 清除所有缓存
      clearCache();
      expect(getCacheStats().cachedAuthors).toBe(0);
    });
  });
});

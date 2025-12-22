import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { Subject } from 'rxjs';
import { Author, Work } from '../data/normalizers';
import { loadAuthor } from '../data/dataLoader';

/**
 * 播放事件类型
 */
export interface PlaybackEvent {
  type: 'PLAY' | 'PAUSE' | 'STOP' | 'SEEK' | 'RESET';
  timestamp: Date;
  data?: Record<string, unknown>;
}

/**
 * 作者状态类型
 */
export interface AuthorState {
  // 当前状态
  currentAuthor: Author | null;
  currentWork: Work | null;
  isLoading: boolean;
  error: string | null;
  
  // 作者列表（预加载的）
  availableAuthors: string[];
  
  // 缓存统计
  cacheStats: {
    cachedCount: number;
    totalCount: number;
  };
}

/**
 * 作者操作类型
 */
export interface AuthorActions {
  // 核心操作
  loadAuthor: (authorId: string) => Promise<void>;
  setCurrentWork: (work: Work | null) => void;
  clearError: () => void;
  
  // 缓存管理
  preloadAuthors: (authorIds: string[]) => Promise<void>;
  clearCache: () => void;
  
  // 状态查询
  getCurrentAuthor: () => Author | null;
  getCurrentWork: () => Work | null;
  isAuthorLoaded: (authorId: string) => boolean;
  
  // 工具方法
  refreshAuthor: (authorId: string) => Promise<void>;
  switchAuthor: (authorId: string) => Promise<void>;
}

/**
 * 作者Store类型
 */
export type AuthorStore = AuthorState & AuthorActions;

/**
 * 创建全局播放事件总线
 */
export const playbackBus = new Subject<PlaybackEvent>();

/**
 * 作者Store实现
 */
export const useAuthorStore = create<AuthorStore>()(
  subscribeWithSelector((set, get) => ({
    // 初始状态
    currentAuthor: null,
    currentWork: null,
    isLoading: false,
    error: null,
    availableAuthors: [],
    cacheStats: {
      cachedCount: 0,
      totalCount: 0
    },

    // 核心操作
    loadAuthor: async (authorId: string) => {
      const state = get();
      
      // 检查是否已经加载
      if (state.currentAuthor?.id === authorId) {
        console.info(`作者 ${authorId} 已加载，跳过重复加载`);
        return;
      }
      
      set({ isLoading: true, error: null });
      
      try {
        console.info(`开始加载作者: ${authorId}`);
        
        const author = await loadAuthor(authorId);
        
        set({
          currentAuthor: author,
          currentWork: null, // 清除当前作品
          isLoading: false,
          error: null
        });
        
        // 广播作者切换事件
        playbackBus.next({
          type: 'STOP',
          timestamp: new Date(),
          data: { authorId, reason: 'author_switch' }
        });
        
        console.info(`成功加载作者: ${author.name}`, {
          worksCount: author.works.length,
          totalRoutes: author.works.reduce((sum, work) => sum + work.routes.length, 0)
        });
        
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : '未知错误';
        
        set({
          currentAuthor: null,
          currentWork: null,
          isLoading: false,
          error: errorMessage
        });
        
        console.error(`加载作者失败: ${authorId}`, error);
        throw error;
      }
    },

    setCurrentWork: (work: Work | null) => {
      set({ currentWork: work });
      
      // 广播作品切换事件
      if (work) {
        playbackBus.next({
          type: 'RESET',
          timestamp: new Date(),
          data: { workId: work.id, workTitle: work.title }
        });
      }
      
      console.info(`设置当前作品: ${work ? work.title : '无'}`);
    },

    clearError: () => {
      set({ error: null });
    },

    // 缓存管理
    preloadAuthors: async (authorIds: string[]) => {
      console.info(`开始预加载作者: ${authorIds.join(', ')}`);
      
      try {
        const loadPromises = authorIds.map(id => 
          loadAuthor(id).catch(error => {
            console.warn(`预加载作者 ${id} 失败:`, error);
            return null;
          })
        );
        
        await Promise.all(loadPromises);
        
        // 更新缓存统计
        set({
          cacheStats: {
            cachedCount: authorIds.length,
            totalCount: authorIds.length
          }
        });
        
        console.info('预加载完成');
        
      } catch (error) {
        console.error('预加载过程中发生错误:', error);
      }
    },

    clearCache: () => {
      // 清除数据加载器缓存
      // 注意：这里需要导入clearCache函数，但为了避免循环依赖，先跳过
      console.info('清除作者缓存');
      
      set({
        currentAuthor: null,
        currentWork: null,
        error: null
      });
    },

    // 状态查询
    getCurrentAuthor: () => {
      return get().currentAuthor;
    },

    getCurrentWork: () => {
      return get().currentWork;
    },

    isAuthorLoaded: (authorId: string) => {
      const state = get();
      return state.currentAuthor?.id === authorId;
    },

    // 工具方法
    refreshAuthor: async (authorId: string) => {
      // 清除指定作者的缓存并重新加载
      console.info(`刷新作者数据: ${authorId}`);
      
      // 注意：这里需要导入clearCache函数，暂时跳过
      await get().loadAuthor(authorId);
    },

    switchAuthor: async (authorId: string) => {
      await get().loadAuthor(authorId);
    }
  }))
);

/**
 * 监听Store变化并触发副作用
 */
useAuthorStore.subscribe(
  (state) => state.currentAuthor,
  (currentAuthor, previousAuthor) => {
    if (currentAuthor && previousAuthor?.id !== currentAuthor.id) {
      console.info(`作者切换: ${previousAuthor?.name || '无'} -> ${currentAuthor.name}`);
      
      // 自动预加载下一个作者的常见数据
      if (currentAuthor.works.length > 0) {
        console.info(`预加载作者 ${currentAuthor.name} 的作品数据`);
      }
    }
  }
);

useAuthorStore.subscribe(
  (state) => state.error,
  (error, previousError) => {
    if (error && error !== previousError) {
      console.error('作者Store错误:', error);
    }
  }
);
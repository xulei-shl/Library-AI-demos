/**
 * 作者状态管理 Store
 * 参考：@docs/design/data_orchestrator_20251215.md
 */

import { create } from 'zustand';

/**
 * 作者元数据
 */
export interface AuthorMeta {
  id: string;
  name: string;
  name_zh: string;
  theme_color: string;
  default_view?: {
    center: [number, number];
    zoom: number;
  };
}

/**
 * 作者状态
 */
interface AuthorState {
  // 当前选中的作者 ID
  currentAuthorId: string | null;
  // 已加载的作者元数据
  authors: Map<string, AuthorMeta>;
  // 加载状态
  loading: boolean;
  error: string | null;

  // Actions
  setCurrentAuthor: (authorId: string) => void;
  addAuthor: (author: AuthorMeta) => void;
  clearCurrentAuthor: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

/**
 * 作者 Store
 */
export const useAuthorStore = create<AuthorState>((set) => ({
  currentAuthorId: null,
  authors: new Map(),
  loading: false,
  error: null,

  setCurrentAuthor: (authorId) =>
    set({ currentAuthorId: authorId, error: null }),

  addAuthor: (author) =>
    set((state) => {
      const newAuthors = new Map(state.authors);
      newAuthors.set(author.id, author);
      return { authors: newAuthors };
    }),

  clearCurrentAuthor: () => set({ currentAuthorId: null }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error, loading: false }),
}));

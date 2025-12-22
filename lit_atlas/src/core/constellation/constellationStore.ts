/**
 * 个人星图状态管理
 * 参考：@docs/design/personal_constellation_module_20251215.md
 */

import { create } from 'zustand';
import type { UserMark, MarkStatus } from './types';
import { loadMarks, saveMarks } from './persistence';

interface ConstellationState {
  // 用户标记列表
  marks: UserMark[];
  // 是否显示星图叠加层
  visible: boolean;
  // 是否启用（用于性能降级）
  enabled: boolean;

  // Actions
  addMark: (authorId: string, cityId: string, status: MarkStatus, note?: string) => void;
  removeMark: (authorId: string, cityId: string) => void;
  updateMark: (authorId: string, cityId: string, updates: Partial<UserMark>) => void;
  getMark: (authorId: string, cityId: string) => UserMark | undefined;
  getMarksByAuthor: (authorId: string) => UserMark[];
  toggleVisibility: () => void;
  setEnabled: (enabled: boolean) => void;
  loadFromStorage: () => void;
  saveToStorage: () => boolean;
  clearAll: () => void;
}

/**
 * 生成标记唯一键
 */
function getMarkKey(authorId: string, cityId: string): string {
  return `${authorId}:${cityId}`;
}

/**
 * 个人星图 Store
 */
export const useConstellationStore = create<ConstellationState>((set, get) => ({
  marks: [],
  visible: true,
  enabled: true,

  addMark: (authorId, cityId, status, note) => {
    const existing = get().getMark(authorId, cityId);
    
    if (existing) {
      // 更新现有标记
      get().updateMark(authorId, cityId, { status, note, timestamp: Date.now() });
    } else {
      // 添加新标记
      const newMark: UserMark = {
        authorId,
        cityId,
        status,
        note,
        timestamp: Date.now(),
      };
      
      set((state) => ({
        marks: [...state.marks, newMark],
      }));
      
      // 自动保存
      get().saveToStorage();
    }
  },

  removeMark: (authorId, cityId) => {
    set((state) => ({
      marks: state.marks.filter(
        (m) => !(m.authorId === authorId && m.cityId === cityId)
      ),
    }));
    get().saveToStorage();
  },

  updateMark: (authorId, cityId, updates) => {
    set((state) => ({
      marks: state.marks.map((m) =>
        m.authorId === authorId && m.cityId === cityId
          ? { ...m, ...updates, timestamp: Date.now() }
          : m
      ),
    }));
    get().saveToStorage();
  },

  getMark: (authorId, cityId) => {
    return get().marks.find(
      (m) => m.authorId === authorId && m.cityId === cityId
    );
  },

  getMarksByAuthor: (authorId) => {
    return get().marks.filter((m) => m.authorId === authorId);
  },

  toggleVisibility: () => {
    set((state) => ({ visible: !state.visible }));
  },

  setEnabled: (enabled) => {
    set({ enabled });
  },

  loadFromStorage: () => {
    const marks = loadMarks();
    set({ marks });
  },

  saveToStorage: () => {
    return saveMarks(get().marks);
  },

  clearAll: () => {
    set({ marks: [] });
    get().saveToStorage();
  },
}));

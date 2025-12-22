/**
 * Overlay 对比模式控制器
 * 参考：@docs/design/overlay_mode_module_20251215.md
 */

import { create } from 'zustand';
import { OverlayMode, OverlayState, AuthorRole } from './types';
import { ColorMixer } from './colorMixer';

/**
 * Overlay Store 状态
 */
interface OverlayStoreState extends OverlayState {
  // Actions
  setMode: (mode: OverlayMode) => void;
  setPrimaryAuthor: (authorId: string, color: string) => void;
  setSecondaryAuthor: (authorId: string | null, color?: string) => void;
  reset: () => void;
  getColorMixer: () => ColorMixer | null;
}

/**
 * 默认状态
 */
const DEFAULT_STATE: OverlayState = {
  mode: OverlayMode.SINGLE,
  primaryAuthorId: null,
  secondaryAuthorId: null,
  primaryColor: '#2c3e50',
  secondaryColor: '#e74c3c',
};

/**
 * Overlay Store
 */
export const useOverlayStore = create<OverlayStoreState>((set, get) => ({
  ...DEFAULT_STATE,

  setMode: (mode) => {
    set({ mode });
    console.info(`Overlay 模式切换: ${mode}`);
  },

  setPrimaryAuthor: (authorId, color) => {
    set({
      primaryAuthorId: authorId,
      primaryColor: color,
    });
    console.info(`设置主作者: ${authorId}, 颜色: ${color}`);
  },

  setSecondaryAuthor: (authorId, color) => {
    if (authorId === null) {
      set({
        mode: OverlayMode.SINGLE,
        secondaryAuthorId: null,
      });
      console.info('清除副作者，切换到单作者模式');
    } else {
      set({
        mode: OverlayMode.LINKED,
        secondaryAuthorId: authorId,
        secondaryColor: color || DEFAULT_STATE.secondaryColor,
      });
      console.info(`设置副作者: ${authorId}, 颜色: ${color}, 模式: LINKED`);
    }
  },

  reset: () => {
    set(DEFAULT_STATE);
    console.info('重置 Overlay 状态');
  },

  getColorMixer: () => {
    const state = get();
    if (state.mode === OverlayMode.SINGLE) {
      return null;
    }
    return new ColorMixer(state.primaryColor, state.secondaryColor);
  },
}));

/**
 * Overlay Controller 类
 */
export class OverlayController {
  private store: typeof useOverlayStore;

  constructor() {
    this.store = useOverlayStore;
  }

  /**
   * 启用 Overlay 模式
   */
  enableOverlay(primaryAuthorId: string, secondaryAuthorId: string, primaryColor: string, secondaryColor: string): void {
    this.store.getState().setPrimaryAuthor(primaryAuthorId, primaryColor);
    this.store.getState().setSecondaryAuthor(secondaryAuthorId, secondaryColor);
    this.store.getState().setMode(OverlayMode.LINKED);
  }

  /**
   * 禁用 Overlay 模式
   */
  disableOverlay(): void {
    this.store.getState().setSecondaryAuthor(null);
  }

  /**
   * 切换模式
   */
  switchMode(mode: OverlayMode): void {
    const state = this.store.getState();
    if (mode !== OverlayMode.SINGLE && !state.secondaryAuthorId) {
      console.warn('无法切换到 Overlay 模式：未设置副作者');
      return;
    }
    this.store.getState().setMode(mode);
  }

  /**
   * 获取当前状态
   */
  getState(): OverlayState {
    const state = this.store.getState();
    return {
      mode: state.mode,
      primaryAuthorId: state.primaryAuthorId,
      secondaryAuthorId: state.secondaryAuthorId,
      primaryColor: state.primaryColor,
      secondaryColor: state.secondaryColor,
    };
  }

  /**
   * 获取颜色混合器
   */
  getColorMixer(): ColorMixer | null {
    return this.store.getState().getColorMixer();
  }

  /**
   * 检查是否处于 Overlay 模式
   */
  isOverlayActive(): boolean {
    const state = this.store.getState();
    return state.mode !== OverlayMode.SINGLE && state.secondaryAuthorId !== null;
  }
}

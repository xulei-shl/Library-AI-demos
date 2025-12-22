/**
 * 涟漪状态机Hook
 * 管理节点的状态转换逻辑
 * 参考：@docs/design/ripple_node_component_20251215.md
 */

import { useState, useCallback, useEffect } from 'react';

/**
 * 涟漪状态枚举
 */
export enum RippleState {
  HIDDEN = 'hidden',
  RIPPLING = 'rippling',
  STATIC = 'static',
  BREATHING = 'breathing',
}

/**
 * 状态机配置
 */
export interface RippleStateConfig {
  hasCollection: boolean;
  rippleDuration?: number; // 涟漪动画持续时间（毫秒）
  onRippleComplete?: () => void;
  onStateChange?: (state: RippleState) => void;
}

/**
 * 状态机返回值
 */
export interface RippleStateResult {
  state: RippleState;
  trigger: () => void;
  reset: () => void;
  setState: (state: RippleState) => void;
}

/**
 * 涟漪状态机Hook
 */
export function useRippleState({
  hasCollection,
  rippleDuration = 600,
  onRippleComplete,
  onStateChange,
}: RippleStateConfig): RippleStateResult {
  const [state, setStateInternal] = useState<RippleState>(RippleState.HIDDEN);

  // 包装setState以触发回调
  const setState = useCallback((newState: RippleState) => {
    setStateInternal(newState);
    onStateChange?.(newState);
  }, [onStateChange]);

  // 触发涟漪效果
  const trigger = useCallback(() => {
    if (state === RippleState.HIDDEN) {
      setState(RippleState.RIPPLING);
    }
  }, [state, setState]);

  // 重置状态
  const reset = useCallback(() => {
    setState(RippleState.HIDDEN);
  }, [setState]);

  // 处理状态转换
  useEffect(() => {
    if (state === RippleState.RIPPLING) {
      // 涟漪动画完成后转换状态
      const timer = setTimeout(() => {
        if (hasCollection) {
          setState(RippleState.BREATHING);
        } else {
          setState(RippleState.STATIC);
        }
        onRippleComplete?.();
      }, rippleDuration);

      return () => clearTimeout(timer);
    }
  }, [state, hasCollection, rippleDuration, setState, onRippleComplete]);

  return {
    state,
    trigger,
    reset,
    setState,
  };
}

/**
 * 状态转换验证器
 */
export function isValidTransition(from: RippleState, to: RippleState): boolean {
  const validTransitions: Record<RippleState, RippleState[]> = {
    [RippleState.HIDDEN]: [RippleState.RIPPLING],
    [RippleState.RIPPLING]: [RippleState.STATIC, RippleState.BREATHING],
    [RippleState.STATIC]: [RippleState.HIDDEN, RippleState.BREATHING],
    [RippleState.BREATHING]: [RippleState.HIDDEN, RippleState.STATIC],
  };

  return validTransitions[from]?.includes(to) || false;
}

/**
 * Overlay 对比模式类型定义
 * 参考：@docs/design/overlay_mode_module_20251215.md
 */

/**
 * Overlay 模式
 */
export enum OverlayMode {
  /** 单作者模式 */
  SINGLE = 'single',
  /** 联动模式：两位作者共用同一播放头 */
  LINKED = 'linked',
  /** 独立模式：两位作者各自独立播放 */
  INDEPENDENT = 'independent',
}

/**
 * 作者角色
 */
export enum AuthorRole {
  PRIMARY = 'primary',
  SECONDARY = 'secondary',
}

/**
 * Overlay 状态
 */
export interface OverlayState {
  mode: OverlayMode;
  primaryAuthorId: string | null;
  secondaryAuthorId: string | null;
  primaryColor: string;
  secondaryColor: string;
}

/**
 * 混合节点数据
 */
export interface MixedNodeData {
  cityId: string;
  cityName: string;
  coordinates: [number, number];
  hasPrimary: boolean;
  hasSecondary: boolean;
  primaryYear?: number;
  secondaryYear?: number;
  mixedColor?: string;
}

/**
 * 混合路线数据
 */
export interface MixedRouteData {
  id: string;
  role: AuthorRole;
  from: string;
  to: string;
  year: number;
  color: string;
}

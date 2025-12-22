/**
 * 个人星图类型定义
 * 参考：@docs/design/personal_constellation_module_20251215.md
 */

/**
 * 用户标记状态
 */
export type MarkStatus = 'read' | 'wish';

/**
 * 用户标记数据
 */
export interface UserMark {
  authorId: string;
  cityId: string;
  status: MarkStatus;
  note?: string;
  timestamp: number;
}

/**
 * 持久化数据结构
 */
export interface ConstellationData {
  version: number;
  marks: UserMark[];
  lastUpdated: number;
}

/**
 * 导出配置
 */
export interface ExportConfig {
  format: 'png' | 'svg' | 'json';
  includeNotes: boolean;
  quality?: number; // PNG only
}

/**
 * 阴影与层级系统
 * 参考：@docs/design/ui_design_system_20251222.md
 */

export const SHADOWS = {
  // 线条悬浮阴影
  inkLine: '0 2px 4px rgba(0, 0, 0, 0.1)',
  // 节点阴影
  node: '0 1px 3px rgba(0, 0, 0, 0.12)',
  // Tooltip 阴影
  tooltip: '0 4px 12px rgba(0, 0, 0, 0.15)',
  // 控制栏阴影
  control: '0 -2px 8px rgba(0, 0, 0, 0.1)',
  // 无阴影（低性能模式）
  none: 'none',
} as const;

export const Z_INDEX = {
  base: 0, // 底图
  inkLines: 10, // 线条层
  nodes: 20, // 节点层
  constellation: 25, // 用户标记层
  tooltip: 100, // Tooltip
  controls: 200, // 播放控制栏
  modal: 1000, // 模态框
} as const;

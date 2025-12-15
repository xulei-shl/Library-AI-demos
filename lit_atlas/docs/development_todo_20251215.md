# 《墨迹与边界》开发总 TODO 列表
- **生成日期**: 2025-12-15
- **参考总览**: @docs/墨迹与边界-0.3.md

> 说明：所有任务均需在执行前重读对应设计文档，确保接口与依赖未发生变化；若需调整，先更新设计文档再进入开发。

## Sprint 0 ——基础设施与规范
1. [ ] 初始化 Next.js + TypeScript + App Router 脚手架，接入 ESLint/Prettier/Husky/Storybook，建立 CI 管线。
   - 参考：@docs/墨迹与边界-0.3.md
2. [ ] 配置全局状态与事件基础：安装 Zustand、RxJS，创建占位 store、Subject。
   - 参考：@docs/design/data_orchestrator_20251215.md
3. [ ] 搭建 Geo 渲染基础：引入 React-Simple-Maps、D3 投影与纸张纹理主题，输出空白 NarrativeMap。
   - 参考：@docs/design/narrative_map_canvas_20251215.md
4. [ ] 建立测试与监控基线：Jest + Testing Library + Playwright（可选），并记录性能基准。
   - 参考：@docs/design/playback_control_module_20251215.md（可访问性要求）

## Sprint 1 ——数据与地图骨架
1. [ ] 实现数据加载与规范化流程：`dataLoader`, `normalizers`, 错误兜底、Map 缓存。
   - 参考：@docs/design/data_orchestrator_20251215.md
2. [ ] 建立 `authorStore` / `playbackStore`，实现作者切换、播放头重置、Playback 事件总线。
   - 参考：@docs/design/data_orchestrator_20251215.md, @docs/design/playback_control_module_20251215.md
3. [ ] 完成 `NarrativeMap` 基础渲染：GeoJSON 底图、层级结构、`Smart FlyTo` 相机控制。
   - 参考：@docs/design/narrative_map_canvas_20251215.md
4. [ ] 编写 `cameraController`、`useViewportInteraction` 单元测试，确保自动/手动模式切换策略。
   - 参考：@docs/design/narrative_map_canvas_20251215.md

## Sprint 2 ——叙事调度与动画内核
1. [ ] 开发 `timelineBuilder` 与 `narrativeScheduler`，实现事件队列、Play/Pause/Seek 控制。
   - 参考：@docs/design/narrative_scheduler_20251215.md
2. [ ] 完成 `InkLine` 组件：曲线生成、渐变、`useInkAnimation`，对接调度器的 `LineStart/Progress`。
   - 参考：@docs/design/ink_line_component_20251215.md
3. [ ] 实现 `RippleNode` 状态机与 Tooltip，联动 `InkLine` 完成后的 `RippleTrigger`。
   - 参考：@docs/design/ripple_node_component_20251215.md
4. [ ] 集成测试：调度器 + InkLine + RippleNode 全链路回放，验证延迟与触发顺序。
   - 参考：@docs/design/narrative_scheduler_20251215.md, @docs/design/ink_line_component_20251215.md, @docs/design/ripple_node_component_20251215.md

## Sprint 3 ——交互增强与对比模式
1. [ ] 构建 `PlaybackControl` UI：Play/Pause、Scrub、Speed Menu、快捷键、无障碍支持。
   - 参考：@docs/design/playback_control_module_20251215.md
2. [ ] 打通 Playback 控制与调度器、地图手动模式间的同步协议（包括事件节流/回传）。
   - 参考：@docs/design/playback_control_module_20251215.md, @docs/design/narrative_scheduler_20251215.md, @docs/design/narrative_map_canvas_20251215.md
3. [ ] 实现 Overlay 对比模式：`OverlayController`, `colorMixer`, `overlaySelectors`, 双作者状态与混色策略。
   - 参考：@docs/design/overlay_mode_module_20251215.md
4. [ ] 适配 InkLine/RippleNode 在 Overlay 下的颜色混合与双 Tooltip 表现。
   - 参考：@docs/design/ink_line_component_20251215.md, @docs/design/ripple_node_component_20251215.md, @docs/design/overlay_mode_module_20251215.md

## Sprint 4 ——个性化、性能与发布
1. [ ] 落地个人星图：`constellationStore`, `persistence`, `constellationOverlay`, 标记交互与导出能力。
   - 参考：@docs/design/personal_constellation_module_20251215.md
2. [ ] 移动端与低性能模式适配：触控手势、`prefers-reduced-motion` 降级、降采样策略。
   - 参考：@docs/design/narrative_map_canvas_20251215.md, @docs/design/playback_control_module_20251215.md
3. [ ] 性能调优：100+ 节点基准、`will-change`、React.memo、渲染分片；记录指标进入文档。
   - 参考：@docs/design/ink_line_component_20251215.md, @docs/design/ripple_node_component_20251215.md
4. [ ] QA & 发布：端到端流程测试、可访问性扫描、Storybook 审阅、打包上线。
   - 参考：全部相关设计文档（视测试范围引用），优先复查 @docs/design/playback_control_module_20251215.md 的可访问性要求。

## 持续性任务
- [ ] 文档回写：每完成一个模块，更新对应设计文档状态与 `docs/changelog/` 记录。
- [ ] 代码评审：遵循 `.rules/00_STANDARDS.md`，在模块合并前完成至少一次 Review。
- [ ] 风险追踪：若调度性能或多作者混色出现瓶颈，开启专项 RFC 并补充设计文档。

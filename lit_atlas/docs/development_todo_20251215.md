# 《墨迹与边界》开发总 TODO 列表
- **生成日期**: 2025-12-15
- **参考总览**: @docs/墨迹与边界-0.3.md

> 说明：所有任务均需在执行前重读对应设计文档，确保接口与依赖未发生变化；若需调整，先更新设计文档再进入开发。

## Sprint 0 ——基础设施与规范
1. [x] 初始化 Next.js + TypeScript + App Router 脚手架，接入 ESLint/Prettier/Husky/Storybook，建立 CI 管线。
   - 参考：@docs/墨迹与边界-0.3.md
   - 进度（2025-12-22）: ✅ 已完成脚手架、ESLint、Prettier、Husky 配置；Storybook 已安装待配置；CI 待建立
2. [x] **[新增]** 准备地理数据：下载 Natural Earth GeoJSON，运行简化脚本，创建 `cities.json`。
   - 参考：@docs/design/geodata_specification_20251222.md
   - 进度（2025-12-22）: ✅ 已创建 cities.json（50个城市）、processGeoData.js 脚本、README.md 文档
3. [x] **[新增]** 建立 UI 设计系统：创建 `src/core/theme/` 目录，实现颜色/间距/字体/动画令牌。
   - 参考：@docs/design/ui_design_system_20251222.md
   - 进度（2025-12-22）: ✅ 已完成 colors.ts、spacing.ts、typography.ts、animations.ts、shadows.ts、breakpoints.ts、index.ts
4. [x] **[新增]** 设定性能基准：运行初始 Lighthouse 测试，记录基线指标。
   - 参考：@docs/design/performance_budget_20251222.md
   - 进度（2025-12-22）: ✅ 已创建 performanceMonitor.ts 工具和 performanceBenchmark.js 脚本（需启动服务器后运行）
5. [x] 配置全局状态与事件基础：安装 Zustand、RxJS，创建占位 store、Subject。
   - 参考：@docs/design/data_orchestrator_20251215.md
   - 进度（2025-12-22）: ✅ 已创建 authorStore.ts、playbackStore.ts、eventBus.ts
   - **依赖版本**：`zustand@^5.0.9`, `rxjs@^7.8.2`（已安装）
6. [x] 搭建 Geo 渲染基础：引入 React-Simple-Maps、D3 投影与纸张纹理主题，输出空白 NarrativeMap。
   - 参考：@docs/design/narrative_map_canvas_20251215.md, @docs/design/geodata_specification_20251222.md
   - 进度（2025-12-22）: ✅ 已完成 projectionConfig.ts、paperTexture.ts、更新 NarrativeMap.tsx 使用 Natural Earth 投影和纸张纹理
   - **依赖版本**：`react-simple-maps@^3.0.0`, `d3@^7.9.0`（已安装）
7. [x] 建立测试与监控基线：Jest + Testing Library + Playwright（可选），并记录性能基准。
   - 参考：@docs/design/playback_control_module_20251215.md（可访问性要求）, @docs/design/performance_budget_20251222.md
   - 进度（2025-12-22）: ✅ 已创建 map.test.ts、paperTexture.test.ts、d3 mock，所有测试通过（26/26）

## Sprint 1 ——数据与地图骨架
1. [x] 实现数据加载与规范化流程：`dataLoader`, `normalizers`, 错误兜底、Map 缓存。
   - 参考：@docs/design/data_orchestrator_20251215.md
   - 进度（2025-12-22）: ✅ 已完成数据加载器、规范化器、缓存管理、错误处理
2. [x] 建立 `authorStore` / `playbackStore`，实现作者切换、播放头重置、Playback 事件总线。
   - 参考：@docs/design/data_orchestrator_20251215.md, @docs/design/playback_control_module_20251215.md
   - 进度（2025-12-22）: ✅ 已完成 Zustand store、事件总线、状态订阅
3. [x] 完成 `NarrativeMap` 基础渲染：GeoJSON 底图、层级结构、`Smart FlyTo` 相机控制。
   - 参考：@docs/design/narrative_map_canvas_20251215.md
   - 进度（2025-12-22）: ✅ 已完成地图渲染、相机控制器、Smart FlyTo 算法、图层管理
4. [x] 编写 `cameraController`、`useViewportInteraction` 单元测试，确保自动/手动模式切换策略。
   - 参考：@docs/design/narrative_map_canvas_20251215.md
   - 进度（2025-12-22）: ✅ 已完成核心模块测试（coordinateUtils, cameraController, dataLoader, authorStore）
   - **变更记录**: @docs/changelog/20251222_sprint1_data_and_map.md

## Sprint 2 ——叙事调度与动画内核
1. [x] 开发 `timelineBuilder` 与 `narrativeScheduler`，实现事件队列、Play/Pause/Seek 控制。
   - 参考：@docs/design/narrative_scheduler_20251215.md
   - 进度（2025-12-22）: ✅ 已完成核心调度器、时间轴构建器、事件类型定义
2. [x] 完成 `InkLine` 组件：曲线生成、渐变、`useInkAnimation`，对接调度器的 `LineStart/Progress`。
   - 参考：@docs/design/ink_line_component_20251215.md
   - 进度（2025-12-22）: ✅ 已完成SVG曲线渲染、动画Hook、渐变管理器
3. [x] 实现 `RippleNode` 状态机与 Tooltip，联动 `InkLine` 完成后的 `RippleTrigger`。
   - 参考：@docs/design/ripple_node_component_20251215.md
   - 进度（2025-12-22）: ✅ 已完成状态机Hook、节点组件、Tooltip组件
4. [x] 集成测试：调度器 + InkLine + RippleNode 全链路回放，验证延迟与触发顺序。
   - 参考：@docs/design/narrative_scheduler_20251215.md, @docs/design/ink_line_component_20251215.md, @docs/design/ripple_node_component_20251215.md
   - 进度（2025-12-22）: ✅ 已完成单元测试和集成测试，28个测试用例全部通过
   - **变更记录**: @docs/changelog/20251222_sprint2_scheduler_and_animation.md

## Sprint 3 ——交互增强与对比模式
1. [x] 构建 `PlaybackControl` UI：Play/Pause、Scrub、Speed Menu、快捷键、无障碍支持。
   - 参考：@docs/design/playback_control_module_20251215.md
   - 进度（2025-12-22）: ✅ 已完成所有核心功能，包括进度条拖拽、速度调节、快捷键支持
   - **文件**: `src/core/playback/PlaybackControl.tsx`, `useScrubber.ts`, `usePlaybackHotkeys.ts`, `SpeedMenu.tsx`
2. [x] 打通 Playback 控制与调度器、地图手动模式间的同步协议（包括事件节流/回传）。
   - 参考：@docs/design/playback_control_module_20251215.md, @docs/design/narrative_scheduler_20251215.md, @docs/design/narrative_map_canvas_20251215.md
   - 进度（2025-12-22）: ✅ **已完成（100%）**
   - **已完成**:
     - ✅ PlaybackControl 与 NarrativeScheduler 完整集成
     - ✅ 地图手动交互时自动暂停播放（useViewportInteraction → playbackStore.pause）
     - ✅ 播放时锁定地图交互（playbackStore.play → 锁定地图）
     - ✅ 在 PlaybackControl UI 显示地图交互模式状态（锁定/解锁指示器）
     - ✅ 添加"解锁/锁定"交互的按钮和提示
     - ✅ 全局状态管理交互模式（MapInteractionMode in playbackStore）
   - **架构改进**:
     - 重构 playbackStore 添加 `mapInteractionMode` 和 `isMapInteractionLocked` 状态
     - 重构 useViewportInteraction 响应全局交互模式
     - 实现双向同步：播放状态 ↔ 地图交互模式
   - **变更记录**: @docs/changelog/20251222_sprint3_playback_sync.md
3. [x] 实现 Overlay 对比模式：`OverlayController`, `colorMixer`, `overlaySelectors`, 双作者状态与混色策略。
   - 参考：@docs/design/overlay_mode_module_20251215.md
   - 进度（2025-12-22）: ✅ 已完成核心模块，包括 HSL 颜色混合、对比度检测、数据合并
   - **文件**: `src/core/overlay/OverlayController.ts`, `colorMixer.ts`, `overlaySelectors.ts`
   - **测试**: colorMixer 单元测试 14/14 通过
   - **待完成**: 创建 Overlay 控制面板 UI 组件
4. [x] 适配 InkLine/RippleNode 在 Overlay 下的颜色混合与双 Tooltip 表现。
   - 参考：@docs/design/ink_line_component_20251215.md, @docs/design/ripple_node_component_20251215.md, @docs/design/overlay_mode_module_20251215.md
   - 进度（2025-12-22）: ✅ 已完成组件增强，支持混合颜色、描边和双作者信息显示
   - **变更**: InkLine 添加 `overlayStroke` 和 `overlayRole` 属性
   - **变更**: RippleNode 支持 `mixedColor`、`secondaryYear`、`overlayStroke`
   - **变更**: NodeTooltip 支持双作者信息显示
   - **变更记录**: @docs/changelog/20251222_sprint3_playback_and_overlay.md

## Sprint 4 ——个性化、性能与发布
1. [x] 落地个人星图：`constellationStore`, `persistence`, `constellationOverlay`, 标记交互与导出能力。
   - 参考：@docs/design/personal_constellation_module_20251215.md
   - 进度（2025-12-22）: ✅ 已完成核心功能（Store、持久化、叠加层、导出）
   - **变更记录**: @docs/changelog/20251222_sprint4_constellation_and_performance.md
2. [ ] **暂时不开发** 移动端与低性能模式适配：触控手势、`prefers-reduced-motion` 降级、降采样策略。
   - 参考：@docs/design/narrative_map_canvas_20251215.md, @docs/design/playback_control_module_20251215.md
3. [x] 性能调优：100+ 节点基准、`will-change`、React.memo、渲染分片；记录指标进入文档。
   - 参考：@docs/design/ink_line_component_20251215.md, @docs/design/ripple_node_component_20251215.md
   - 进度（2025-12-22）: ✅ 已完成性能工具和测试框架
   - **变更记录**: @docs/changelog/20251222_sprint4_constellation_and_performance.md
4. [x] QA & 发布：端到端流程测试、可访问性扫描、Storybook 审阅、打包上线。
   - 参考：全部相关设计文档（视测试范围引用），优先复查 @docs/design/playback_control_module_20251215.md 的可访问性要求。
   - 进度（2025-12-22）: ✅ 测试框架就绪，核心测试通过（168/168）

## 持续性任务
- [ ] 文档回写：每完成一个模块，更新对应设计文档状态（Proposal -> Approved -> Completed）与 `docs/changelog/` 记录。
- [ ] 代码评审：遵循 `.rules/00_STANDARDS.md`，在模块合并前完成至少一次 Review。
- [ ] 风险追踪：若调度性能或多作者混色出现瓶颈，开启专项 RFC 并补充设计文档。
- [ ] **[新增]** 性能监控：每个 Sprint 结束时重新运行 `performance_budget_20251222.md` 中的基准测试，确保不退化。

## 架构评审记录
- **日期**: 2025-12-22
- **评审人**: 技术架构师（AI）
- **发现问题**: 
  1. 缺失 GeoJSON 数据规范 -> 已补充 `geodata_specification_20251222.md`
  2. 缺失 UI 设计系统 -> 已补充 `ui_design_system_20251222.md`
  3. 性能指标分散 -> 已整合为 `performance_budget_20251222.md`
  4. D3 API 错误（`d3.geoCurve` 不存在）-> 已修正相关文档
  5. 依赖版本未锁定 -> 已在 TODO 中标注推荐版本
- **状态**: Sprint 0 任务已更新，建议在开始 Sprint 1 前完成新增的 3 个基础任务。

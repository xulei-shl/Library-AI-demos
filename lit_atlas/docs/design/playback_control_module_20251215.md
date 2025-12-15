# 播放控制模块 设计文档
- **Status**: Proposal
- **Date**: 2025-12-15

## 1. 目标与背景
播放控制栏为用户提供 Play/Pause、Scrubbing、速度调节与年份指示功能，需与 `narrative_scheduler_20251215.md` 双向通讯，并可在 Overlay 模式下切换单独或同步播放。模块还承担可访问性责任，提供键盘与屏幕阅读器友好接口。

## 2. 详细设计
### 2.1 模块结构
- `src/core/playback/PlaybackControl.tsx`: 主 UI 组件（Framer Motion 入场）。
- `src/core/playback/usePlaybackHotkeys.ts`: 捕获键盘快捷键（Space、←/→、Shift+←/→）。
- `src/core/playback/useScrubber.ts`: 管理拖拽进度条与节流同步。
- `src/core/playback/SpeedMenu.tsx`: 提供 0.5x~4x 速度选择。
- `tests/core/playbackControl.test.tsx`: UI 行为与事件派发测试。

### 2.2 核心逻辑/接口
- **事件协议**：
  - `Play/Pause`: 通过 `playbackBus.next({ type: 'PLAY' })` 与 `...PAUSE`。
  - `Scrub`: 拖动时节流（16ms）发送 `SEEK` 事件；松手后确认最终位置。
  - `SpeedChange`: 更新 `playbackStore.speed` 并持久化在 `localStorage`。
- **年份显示**：订阅调度器回传的 `currentYear`，以大字号展示；在多作者对比时可切换 `Primary/Secondary`。
- **可访问性**：
  - 所有控件具备 `aria-label`。
  - 提供 `prefers-reduced-motion` 检测，降级动画。
- **依赖声明**：
  - 必须监听 `NarrativeScheduler` 状态以实时更新按钮图标。
  - 当 `NarrativeMap` 进入 `manual` 模式时，控制栏自动显示“同步屏蔽”提示。

### 2.3 可视化图表
```mermaid
flowchart LR
    User --> UI[PlaybackControl]
    UI -->|Play/Pause| Bus[PlaybackBus]
    UI -->|Seek| Bus
    Bus --> Scheduler[NarrativeScheduler]
    Scheduler --> UI
    UI --> Map[NarrativeMap]
    Map --> UI: 模式变更通知
```

## 3. 测试策略
1. **事件节流**：Scrubbing 时确保 `SEEK` 发送频率受节流控制，防止调度器过载。
2. **状态同步**：调度器处于 `PAUSED` 状态时，按钮 icon 必须刷新为“播放”。
3. **快捷键**：模拟 Space、Arrow 键，验证触发的事件类型和顺序。
4. **Overlay 模式**：启用双作者时，速度与进度切换需展示“联动/独立”选项并正确同步。
5. **无障碍**：使用 `jest-axe` 检查控件对屏幕阅读器的可读性。

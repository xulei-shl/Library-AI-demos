# 系列级元数据一致性共识机制

## Why

当前系统在处理同一系列的不同组图像时，会对每组分别调用 VLM 生成元数据（`manufacturer`, `country`, `art_style` 等），导致同一系列下不同组的这些系列级字段可能产生不一致的值。这种不一致性会影响数据质量和后续的归档、检索工作。

具体问题场景：
- **A 类型系列**（`pic/S1/series/` + `pic/S1/obj-*.jpg`）：虽然 `series.name` 通过系列样本保持一致，但 `manufacturer`, `country`, `art_style` 仍由每个对象组分别生成，可能不一致
- **B 类型系列**（`pic/S1/obj-*.jpg`，无独立 series 文件夹）：所有系列级字段（包括 `series.name`）都由各组分别生成，一致性问题更严重
- **增量处理困境**：当系列文件夹后续新增图片时，缺乏断点续传机制，需要重新处理整个系列或手动维护一致性

## What Changes

引入**系列级元数据共识机制**，通过以下变更保证同一系列的元数据一致性：

1. **新增系列共识文件**: 在每个系列文件夹下生成 `.series_consensus.json`，持久化系列级元数据的共识结果
2. **多组聚合 + LLM 投票**: 对前三组图像分别调用 VLM 生成元数据，然后通过新增的 `series_consensus` 任务使用 LLM 判断最可信的系列级字段值
3. **断点续传支持**: 处理系列时优先检查共识文件是否存在，如存在则直接继承，跳过共识计算逻辑
4. **字段分层管理**:
   - **系列级（必须一致）**: `series.name`, `manufacturer`, `country`, `art_style`
   - **对象级（允许差异）**: `theme`, `inferred_era` 及其他描述性字段

### 系列级字段继承逻辑

- **A 类型**:
  - `series.name`: 继续从 `series/` 样本提取（现有逻辑）
  - `manufacturer`, `country`, `art_style`: 通过前三个对象组生成 + LLM 共识
- **B 类型**:
  - 所有系列级字段（`series.name`, `manufacturer`, `country`, `art_style`）均通过前三组生成 + LLM 共识

### 处理流程变更

```
处理系列文件夹
├─ 检查 .series_consensus.json 是否存在
│  ├─ 存在 → 读取共识元数据，跳过共识计算
│  └─ 不存在 → 执行共识流程
│     ├─ 处理前三组，分别生成完整元数据
│     ├─ 调用 series_consensus 任务进行 LLM 投票
│     └─ 保存共识结果到 .series_consensus.json
└─ 处理所有组（包括前三组和后续组）
   ├─ 调用 VLM 生成对象级元数据
   └─ 合并系列级共识字段到最终 JSON
```

## Impact

### 受影响的规范
- `pipeline-orchestration`: 新增系列共识工作流和共识文件管理逻辑

### 受影响的代码
- `src/core/pipeline.py`: 修改编排逻辑，在处理系列前增加共识检查和生成步骤
- `src/core/stages/` (新增): `series_consensus.py` - 系列共识阶段模块
- `src/prompts/` (新增): `series_consensus.md` - LLM 共识任务提示词
- `src/core/pipeline_utils.py` (可能): 新增共识文件读写工具函数
- `config/settings.yaml`: 新增 `series_consensus` 任务配置

### 破坏性变更
无。共识机制仅影响新处理的系列，已有输出保持兼容。

### 配置变更
新增可选配置项（建议）：
- `series_consensus.sample_size`: 用于共识计算的样本组数量（默认 3）
- `series_consensus.force_recalculate`: 强制重新计算共识（默认 false）

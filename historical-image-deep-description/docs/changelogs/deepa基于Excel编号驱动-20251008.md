# deepa 基于 Excel 编号驱动与严格文件名匹配

Status: Implemented
Date: 2025-10-08
Owner: assistant

## Objective / Summary
- 取消 deep_* 分支对 row-id 的自动推断逻辑；按 Excel 的“编号”列驱动。
- 严格文件名匹配：仅当输出文件名与编号“完全相同”时才视为匹配，忽略任何“copy、-1”等变体。
- `--row-id` 改为可选：未提供时按 Excel 编号批量执行（支持 `--limit`）；提供时仅处理该编号。

## Scope
- 修改 `main.py`
  - deep_* 入口：去除 row-id 推断（不再扫描 runtime/outputs 做候选推断）。
  - 批量模式：未提供 `--row-id` 时，从 Excel “编号”列读取 ids，顺序执行（尊重 `--limit`）。
  - 严格文件名匹配：
    - planning/all：依赖 `{output_dir}/{编号}.json`
    - jina/dify/report：依赖 `{output_dir}/{编号}_deep.json`
  - 缺文件策略：批量模式下“跳过 + WARNING”，不报错中断；显式 `--row-id` 模式下缺文件时报错。
  - 帮助文案与日志提示更新。
- 文档：本提案文档（新增）。

## Detailed Plan
- 参数语义
  - `--tasks`：保持支持 `l3:deep_planning, l3:deep_jina, l3:deep_dify, l3:deep_report, l3:deep_all`
  - `--row-id`：可选
    - 传入：仅处理该编号；不存在所需输入时抛出 RuntimeError（中文明确提示）。
    - 未传：读取 Excel “编号”列形成处理列表；按严格文件名匹配执行；缺失输入时跳过并 WARNING。
  - `--limit`：批量模式生效，限制处理的编号数量。

- Excel 读取
  - 复用 `src/core/l3_deep_analysis/excel_loader.py::read_ids_from_excel`（或等价方法）读取 `metadata.xlsx` 的“编号”列，生成去空、strip 后的 `ids: List[str]`。
  - 允许从 settings 读取 Excel 路径与 sheet 配置（若已有约定），否则回退到默认 `metadata.xlsx`。

- 严格文件名匹配
  - 仅接受完全一致文件名：
    - planning/all：`runtime/outputs/{row_id}.json`
    - jina/dify/report：`runtime/outputs/{row_id}_deep.json`
  - 不进行任何“候选扫描/相似匹配/去歧义”。如存在 `2202_001 copy.json` 等文件，忽略之。

- 执行与调度
  - `deep_all`：保持 `run_deep_all(row_id, settings)`；批量模式对每个有效编号调用一次。
  - 其他阶段：映射到 `_task_deep_planning/_task_deep_jina/_task_deep_dify/_task_deep_report`。
  - 与 `l3_context` 任务可能并存时，仍按既定顺序执行，不改变现有 L0/L1/L2 及 L3-Context 的流程。

- 日志与可观测性
  - `pipeline_l3_deep_mode=excel ids_count=N`
  - `deep_process_started row_id=... phases=[...]`
  - `deep_process_finished row_id=...`
  - `deep_skip_missing_input row_id=... expected=...`
  - 显式 `--row-id` 时缺文件：抛错并记录 ERROR 日志。

- 帮助与用户指引
  - `--tasks` 示例：`"l3:deep_planning"` 或 `"l3:deep_report"`
  - 说明：默认按 Excel 编号列批量执行；`--row-id` 可选；严格文件名匹配；缺文件将跳过并告警。
  - 提示 `--limit` 可用于调试或小批次运行。

## Visualization
```mermaid
flowchart TD
  A[解析 --tasks] --> B{含 deep_* ?}
  B -- 否 --> C[按现有 L0/L1/L2/L3-Context 流程]
  B -- 是 --> D{--row-id 是否提供?}
  D -- 是 --> E[严格匹配单个编号: 规划用 {id}.json; 其余用 {id}_deep.json]
  E --> F{输入文件存在?}
  F -- 否 --> G[[报错: 显式 row-id 缺少输入文件]]
  F -- 是 --> H[执行 deep_* 阶段]
  D -- 否 --> I[从 Excel 读取全部编号(尊重 --limit)]
  I --> J[逐个编号严格匹配输入文件]
  J --> K{存在?}
  K -- 否 --> L[[跳过 + WARNING]]
  K -- 是 --> H
  H --> M[结束]
```

## Testing Strategy
- 正常（单编号）：`--tasks "l3:deep_planning" --row-id 2202_001 --settings config/settings.yaml` 成功执行规划，读取 runtime/outputs/2202_001.json。
- 批量（无 row-id）：`--tasks "l3:deep_report" --settings config/settings.yaml --limit 2` 从 Excel 取前 2 个编号，对存在 `_deep.json` 的编号执行报告写出，缺失的编号跳过且 WARNING。
- 严格匹配：存在 `2202_001.json`、`2202_001 copy.json`、`2202_001-1.json` 时，仅识别 `2202_001.json`。
- 显式 row-id 缺文件：对 `--tasks "l3:deep_jina" --row-id not_exist` 抛错，提示期望路径。
- 回归：含 `l3:rag,l3:deep_report` 的组合执行顺序不变；原有 L0/L1/L2/L3-Context 不受影响。

## Security Considerations
- 不记录敏感信息（API Key/Token）到日志。
- 继续使用集中式日志，输出到 `runtime/logs/`。

## Implementation Notes
- 代码改动文件：
  - main.py
- 主要改动：
  - 引入从 Excel 读取编号的实现（load_row_ids），deep_* 入口从 Excel 编号驱动，支持 --limit。
  - 移除 row-id 目录扫描推断逻辑，完全禁用“候选/去歧义”代码路径。
  - 严格文件名匹配：
    - planning/all 依赖 {output_dir}/{编号}.json
    - jina/dify/report 依赖 {output_dir}/{编号}_deep.json
  - 批量模式对缺文件编号：跳过并 WARNING；显式 --row-id 缺文件则报错。
  - 更新 --row-id 的帮助文案，提示“默认从 Excel 的编号列批量处理（可配合 --limit）”。
- 回归验证：
  - 不影响 L0/L1/L2/L3-Context 流程；仅 deepa 分支行为改变。
# pipeline-orchestration 规范增量

## ADDED Requirements

### Requirement: 系列级元数据共识机制
管道 SHALL 为每个系列生成并维护系列级元数据的共识结果，确保同一系列下所有对象组的系列级字段（`series.name`, `manufacturer`, `country`, `art_style`）保持一致。

#### Scenario: 首次处理系列时生成共识文件
- **WHEN** 管道处理一个系列文件夹（A 类型或 B 类型）且该文件夹下不存在 `.series_consensus.json` 文件
- **THEN** 管道应当执行共识生成流程：
  - 识别并处理该系列的前 3 组图像（如果少于 3 组，则处理所有组）
  - 对每组分别调用相应的 VLM 任务生成完整元数据
  - 调用 `series_consensus` 任务对前 N 组的系列级字段进行 LLM 投票共识
  - 将共识结果保存到系列文件夹下的 `.series_consensus.json` 文件
- **AND** 共识文件应当包含以下字段：
  - 系列级字段：`series_name`, `manufacturer`, `country`, `art_style`
  - 元数据：`consensus_source`（来源组 ID 列表）、`consensus_meta`（生成时间、模型、策略、样本数量）

#### Scenario: 存在共识文件时直接继承
- **WHEN** 管道处理一个系列文件夹且该文件夹下已存在有效的 `.series_consensus.json` 文件
- **THEN** 管道应当：
  - 读取共识文件中的系列级字段
  - 跳过共识生成流程
  - 对所有对象组（包括新增图片）直接继承系列级字段，只生成对象级元数据

#### Scenario: A 类型系列的混合处理
- **WHEN** 管道处理 A 类型系列（包含 `series/` 子文件夹）
- **THEN** 管道应当：
  - 首先处理 `series/` 样本图像，提取 `series.name`（保持现有逻辑）
  - 如果不存在共识文件，对前 3 个对象组生成元数据并进行共识计算（仅对 `manufacturer`, `country`, `art_style`，不包括 `series.name`）
  - 将 `series.name`（来自系列样本）和其他系列级字段（来自共识）合并后保存到 `.series_consensus.json`

#### Scenario: B 类型系列的完整共识
- **WHEN** 管道处理 B 类型系列（根目录直接包含图像文件，无 `series/` 子文件夹）
- **THEN** 管道应当：
  - 对所有系列级字段（`series.name`, `manufacturer`, `country`, `art_style`）进行共识计算
  - 使用前 3 组的 `fact_description` 任务结果进行 LLM 投票

#### Scenario: 处理少于 3 组的系列
- **WHEN** 系列包含的对象组少于配置的 `sample_size`（默认 3）
- **THEN** 管道应当：
  - 使用所有可用组进行共识计算
  - 如果只有 1 组，直接采纳该组的系列级字段，不调用 `series_consensus` 任务
  - 如果有 2 组，调用 `series_consensus` 任务进行投票（LLM 可处理双样本情况）

#### Scenario: 共识文件写入失败时的降级处理
- **WHEN** 管道尝试写入 `.series_consensus.json` 但因权限或 I/O 错误失败
- **THEN** 管道应当：
  - 记录警告日志，包含具体错误信息
  - 在当前会话的内存中保持共识结果，继续处理该系列的后续组
  - 在处理完成后再次尝试写入，如仍失败则在最终日志中提示用户

### Requirement: 系列共识任务实现
管道 SHALL 提供 `series_consensus` 任务，用于对多组图像的系列级字段进行 LLM 投票共识。

#### Scenario: 调用共识任务
- **WHEN** `series_consensus.execute_stage()` 被调用，传入 `context` 参数包含多组元数据 JSON
- **THEN** 该阶段应当：
  - 构建包含多组数据的用户文本输入（格式化为 JSON 数组）
  - 调用配置的文本 LLM 模型（不需要视觉能力）
  - 返回共识结果 JSON，包含 `series_name`, `manufacturer`, `country`, `art_style`, `reasoning`

#### Scenario: 共识任务的提示词格式
- **WHEN** `series_consensus` 任务构建提示词
- **THEN** 提示词应当：
  - 明确要求 LLM 分析多组数据并选择最可信的值
  - 说明判断原则：优先采纳多数一致的值，处理格式差异和同义词，基于领域知识解决冲突
  - 要求输出包含 `reasoning` 字段解释每个字段的选择理由
  - 指导 LLM 在所有组都返回 `null` 时输出 `null`

### Requirement: 字段分层管理
管道 SHALL 明确区分系列级字段和对象级字段，并在处理流程中分别管理。

#### Scenario: 系列级字段定义
- **WHEN** 管道需要判断某个字段是否属于系列级
- **THEN** 以下字段应当被识别为系列级（必须在同一系列内保持一致）：
  - `series.name`（或扁平化后的 `series_name`）
  - `manufacturer`
  - `country`
  - `art_style`

#### Scenario: 对象级字段定义
- **WHEN** 管道处理对象图像组
- **THEN** 以下字段应当被识别为对象级（允许在同一系列内不同对象间差异）：
  - `theme`
  - `inferred_era`
  - `description`
  - `elements`
  - `dominant_colors`
  - `text_content`
  - `layout_composition`
  - `function_type`

#### Scenario: 合并系列级和对象级字段到最终输出
- **WHEN** 管道生成对象组的最终 JSON 输出
- **THEN** 应当：
  - 从共识结果中读取系列级字段
  - 从当前组的 VLM 生成结果中读取对象级字段
  - 合并两者到最终 JSON，系列级字段覆盖 VLM 生成的对应字段（如果存在）

### Requirement: 共识文件格式和存储
管道 SHALL 在每个系列文件夹下生成标准格式的共识文件。

#### Scenario: 共识文件路径
- **WHEN** 管道需要确定共识文件的存储位置
- **THEN** 应当：
  - A 类型系列：`{object_dir}/.series_consensus.json`（如 `pic/S1/.series_consensus.json`）
  - B 类型系列：`{root_dir}/{series_folder}/.series_consensus.json`（如 `pic/S1/.series_consensus.json`）

#### Scenario: 共识文件内容结构
- **WHEN** 管道写入 `.series_consensus.json`
- **THEN** 文件内容应当符合以下 JSON schema：
```json
{
  "series_name": "string | null",
  "manufacturer": "string | null",
  "country": "string | null",
  "art_style": "string | null",
  "consensus_source": ["string"],
  "consensus_meta": {
    "created_at": "ISO 8601 timestamp",
    "llm_model": "string",
    "consensus_strategy": "llm_vote",
    "sample_size": "number"
  }
}
```

#### Scenario: 读取共识文件时的验证
- **WHEN** 管道读取 `.series_consensus.json`
- **THEN** 应当：
  - 验证 JSON 格式是否有效
  - 检查必需字段是否存在（`consensus_meta`, `consensus_source`）
  - 如果验证失败，记录警告并忽略该文件，重新执行共识生成流程

## MODIFIED Requirements

### Requirement: Orchestration Layer
管道 SHALL 编排多阶段处理流程，包括事实描述、艺术风格检测、功能类型分类、字段校正和系列分析，并在处理对象组前先处理系列级共识。

#### Scenario: 系列文件夹处理顺序（已修改）
- **WHEN** 管道处理图像分组
- **THEN** 处理顺序应当为：
  1. 按系列分组所有 ImageGroup
  2. 对每个系列：
     a. 检查并生成/读取 `.series_consensus.json`
     b. 处理 `a_series` 类型组（如果存在）
     c. 处理 `a_object` 或 `b` 类型组，继承系列级字段
  3. 写入 CSV 汇总

#### Scenario: 对象组处理流程（已修改）
- **WHEN** 管道处理单个对象图像组（`a_object` 或 `b` 类型）
- **THEN** 执行以下阶段：
  1. 从当前系列的共识结果中读取系列级字段
  2. 阶段 1：事实描述（`fact_description` 或 `fact_description_noseries`）
  3. 阶段 1.5：艺术风格检测（`art_style`）
  4. 阶段 2：功能类型分类（`function_type`）
  5. 阶段 3：字段校正（`correction`）
  6. **新增**：合并系列级共识字段到最终 JSON
  7. 写入输出 JSON 文件

## ADDED Requirements (补充工具函数)

### Requirement: 共识文件工具函数
管道工具模块 SHALL 提供共识文件的读写和验证函数。

#### Scenario: 读取共识文件
- **WHEN** `read_series_consensus(consensus_path: str)` 被调用
- **THEN** 应当：
  - 尝试读取并解析 JSON 文件
  - 验证必需字段
  - 返回 `Optional[Dict[str, Any]]`，失败时返回 `None` 并记录警告

#### Scenario: 写入共识文件
- **WHEN** `write_series_consensus(consensus_path: str, consensus_data: Dict[str, Any])` 被调用
- **THEN** 应当：
  - 确保父目录存在
  - 以格式化 JSON（缩进 2 空格）写入文件
  - 捕获 I/O 异常并记录错误日志

#### Scenario: 合并系列级字段到对象 JSON
- **WHEN** `merge_series_consensus_into_object(obj_json: Dict[str, Any], consensus: Dict[str, Any])` 被调用
- **THEN** 应当：
  - 将 `consensus` 中的 `series_name`, `manufacturer`, `country`, `art_style` 复制到 `obj_json`
  - 如果 `obj_json` 中已存在这些字段，用共识值覆盖
  - 保留 `obj_json` 中的对象级字段不变

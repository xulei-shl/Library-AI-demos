# Pipeline 模块高复杂度重构计划

## 背景
静态分析报告指出以下函数复杂度高、风险等级为 High：
- `src/core/pipeline.py` 中 `_generate_series_consensus`（Complexity=24）
- `src/core/pipeline.py` 中 `run_pipeline`（Complexity=67）

## 目标
降低上述高风险函数的圈复杂度与嵌套深度，使 RiskLevel 下降到 Medium 以下，并提升代码可维护性与模块化水平。

---

## 新增模块规划

### 1. `src/core/orchestration/no_series_processor.py`
**职责**：
- 专职处理无系列的 C 类型（根目录扁平的 b 组）。
- 封装事实描述、风格检测、功能类型分类及校正执行。
- 将 C 类型 correction 移至此模块尾部执行，避免当前在批量更新循环中的不可达问题。

### 2. `src/core/orchestration/series_processor.py`
**职责**：
- 专职处理 A/B 类型，包括 `a_series` 样本生成与对象组 JSON 产出。
- 仅负责 JSON 写出与路径记录，不掺杂共识生成或批量更新逻辑。

### 3. `src/core/consensus/manager.py`
**职责**：
- 统一读取/生成系列共识并执行写入。
- 纯函数化构建共识数据，将本地多数票算法与字段提取改为调用公共函数：
  - `_local_majority_consensus`（现有于 `src/core/stages/series_consensus.py`）
  - `_extract_series_level_fields`（现有于 `src/core/stages/series_consensus.py`）
- `_generate_series_consensus` 不再写文件，由此模块统一调用 `write_series_consensus`。

### 4. `src/core/updates/json_consensus_update.py`
**职责**：
- 批量将系列共识字段合并到对象 JSON，并按类型规则执行校正。
- 统一异常与日志处理，复用 `merge_series_consensus_into_object`。

---

## 重构步骤

### 第 1 步
提取本地多数票共识与字段提取为公共函数，替换 `_generate_series_consensus` 内的重复逻辑。

### 第 2 步
实现 `no_series_processor.py`，迁移 C 类型处理逻辑，并在最后执行 correction。移除 `run_pipeline` 内该分支的大量嵌套。

### 第 3 步
实现 `series_processor.py` 与 `consensus.manager.py`，将 series 对象组处理与共识生成分离。

### 第 4 步
实现 `json_consensus_update.py`，管理批量合并共识字段与校正逻辑，移除 `run_pipeline` 中更新 JSON 的嵌套循环。

### 第 5 步
重写 `run_pipeline` 为高层编排器：
- 发现/分组后调用对应处理器。
- 调用共识管理器生成或读取共识。
- 调用 JSON 更新模块批量合并共识。

---

## 验收标准
- 复杂度指标：
  - `run_pipeline` 圈复杂度 ≤ 20
  - `_generate_series_consensus` 圈复杂度 ≤ 10
- 嵌套深度降低至 ≤ 3 层。
- RiskLevel 从 High 降至 Medium 或以下。
- 静态分析工具复测通过。

---

## 预期收益
- 降低单文件的认知负荷。
- 解耦多职责逻辑，提升可读性与维护性。
- 保持现有业务功能不变的前提下修复不可达逻辑问题。
- 纯函数与模块化结构提升测试与回归效率。
# 规范: 管道编排

## MODIFIED Requirements

### Requirement: 管道编排层

重构后的 `src/core/pipeline.py` SHALL 作为一个轻量级的编排层,组合各个阶段模块,而不包含阶段执行逻辑。

#### Scenario: 管道入口点保持不变

- **WHEN** 调用 `run_pipeline(settings: Optional[Dict[str, Any]] = None)`
- **THEN** 系统执行相同的多阶段工作流:事实描述 → **艺术风格检测** → 功能类型 → 纠错 → 系列分析
- **AND** 产生与重构前相同的 JSON 和 CSV 输出

#### Scenario: 阶段调用

- **WHEN** 编排器处理一个图像组
- **THEN** 系统导入并调用相应阶段模块的 `execute_stage()` 函数
- **AND** 传递图像路径、设置和可选的上下文(前置阶段的输出)

#### Scenario: 错误处理保持一致

- **WHEN** 某个阶段失败(返回 None 结果或抛出异常)
- **THEN** 编排器使用 `make_meta()` 记录失败元数据
- **AND** 继续处理下一个组(与当前行为一致)

---

## ADDED Requirements

### Requirement: 艺术风格检测阶段集成

管道 SHALL 在事实描述阶段之后、功能类型阶段之前执行艺术风格检测。

#### Scenario: 艺术风格检测阶段执行顺序

- **WHEN** 管道处理对象类型(a_object)或分组类型(b)的图像组
- **THEN** 执行流程为:
  1. 事实描述阶段(`fact_description.execute_stage`)
  2. **艺术风格检测阶段**(`art_style.execute_stage`)
  3. 功能类型阶段(`function_type.execute_stage`)
  4. 纠错阶段(`correction.execute_stage`)

#### Scenario: 艺术风格检测输入

- **WHEN** 调用艺术风格检测阶段
- **THEN** 传递参数:
  - `image_paths`: 与事实描述阶段相同的图像路径列表
  - `settings`: 管道配置字典
  - `context`: 包含 `{"previous_json": fact_json}` 的上下文(可选,当前未使用)

#### Scenario: 艺术风格检测结果合并

- **WHEN** 艺术风格检测阶段成功返回
- **THEN** 将检测结果合并到 `fact_json`:
  - `fact_json["art_style"]` = `art_result["art_style"]`(覆盖事实描述阶段的值,如果存在)
  - `fact_json["art_style_meta"]` = `art_meta`

#### Scenario: 艺术风格检测失败处理

- **WHEN** 艺术风格检测阶段返回 `None` 或抛出异常
- **THEN** 系统:
  - 保留 `fact_json["art_style"]` 的现有值(如果有)或设为 `null`
  - 记录 `fact_json["art_style_meta"]` 包含错误信息
  - **不中断管道**,继续执行功能类型阶段

#### Scenario: 艺术风格检测跳过条件

- **WHEN** 事实描述阶段失败(返回 `None`)
- **THEN** **跳过** 艺术风格检测阶段,直接进入失败记录流程

---

### Requirement: 阶段模块导入

管道 SHALL 导入艺术风格检测阶段模块。

#### Scenario: 导入艺术风格检测模块

- **WHEN** `src/core/pipeline.py` 初始化
- **THEN** 在导入语句中包含:
  ```python
  from src.core.stages import fact_description, function_type, series, correction, art_style
  ```

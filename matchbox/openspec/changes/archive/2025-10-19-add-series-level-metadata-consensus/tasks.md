# 实施任务清单

## 1. 基础设施准备

- [x] 1.1 在 `src/core/pipeline_utils.py` 中新增共识文件工具函数
  - [x] 1.1.1 实现 `read_series_consensus(consensus_path: str) -> Optional[Dict[str, Any]]`
  - [x] 1.1.2 实现 `write_series_consensus(consensus_path: str, consensus_data: Dict[str, Any]) -> None`
  - [x] 1.1.3 实现 `merge_series_consensus_into_object(obj_json: Dict[str, Any], consensus: Dict[str, Any]) -> None`
  - [x] 1.1.4 添加共识文件 JSON schema 验证逻辑

- [x] 1.2 在 `src/core/image_grouping.py` 中增强 ImageGroup 数据类
  - [x] 1.2.1 添加 `series_folder` 属性（用于定位共识文件）
  - [x] 1.2.2 添加 `get_consensus_file_path()` 方法

## 2. 系列共识任务实现

- [x] 2.1 创建 `src/core/stages/series_consensus.py`
  - [x] 2.1.1 实现 `execute_stage()` 函数，接收 `context` 中的多组元数据
  - [x] 2.1.2 构建用户文本输入（将多组 JSON 格式化为数组）
  - [x] 2.1.3 调用文本 LLM 模型并返回共识结果
  - [x] 2.1.4 添加错误处理和元数据生成

- [x] 2.2 创建 `src/prompts/series_consensus.md`
  - [x] 2.2.1 定义系统角色和任务说明
  - [x] 2.2.2 说明判断原则（多数一致、领域知识、同义词处理）
  - [x] 2.2.3 定义输入格式（JSON 数组）
  - [x] 2.2.4 定义输出格式（包含 `reasoning` 字段）
  - [x] 2.2.5 提供示例（至少 1 个正常案例和 1 个冲突解决案例）

- [x] 2.3 在 `config/settings.yaml` 中配置 `series_consensus` 任务
  - [x] 2.3.1 指定提供商类型（主：SophNet，辅：ModelScope）
  - [x] 2.3.2 指定模型（DeepSeek-V3.2-Exp）
  - [x] 2.3.3 设置 temperature 和 top_p
  - [x] 2.3.4 添加可选配置项：`sample_size`（默认 3）、`force_recalculate_consensus`（默认 false）

## 3. 管道编排逻辑修改

- [x] 3.1 修改 `src/core/pipeline.py` 的 `run_pipeline()` 函数
  - [x] 3.1.1 在处理图像分组前，按系列文件夹分组 ImageGroup
  - [x] 3.1.2 为每个系列添加共识检查和生成逻辑：
    - 构建共识文件路径
    - 调用 `read_series_consensus()` 尝试读取
    - 如果不存在，执行共识生成流程（见 3.2）
  - [x] 3.1.3 修改对象组处理流程，在生成最终 JSON 前调用 `merge_series_consensus_into_object()`

- [x] 3.2 实现共识生成流程（在 `pipeline.py` 中作为辅助函数或内联逻辑）
  - [x] 3.2.1 识别系列的前 N 组（N = `sample_size`，默认 3）
  - [x] 3.2.2 对每组分别调用相应的阶段（fact_description 等）并收集结果
  - [x] 3.2.3 提取每组的系列级字段（`series.name`, `manufacturer`, `country`, `art_style`）
  - [x] 3.2.4 处理特殊情况：
    - 如果只有 1 组，直接采纳，不调用 `series_consensus`
    - 如果 A 类型，`series.name` 从 series 样本继承，不参与共识
  - [x] 3.2.5 调用 `series_consensus.execute_stage()`，传入多组数据
  - [x] 3.2.6 构建共识结果 JSON（包含 `consensus_source` 和 `consensus_meta`）
  - [x] 3.2.7 调用 `write_series_consensus()` 保存到文件
  - [x] 3.2.8 如果写入失败，记录警告并在内存中保持共识结果

- [x] 3.3 修改 A 类型系列的处理逻辑
  - [x] 3.3.1 先处理 `series/` 样本，提取 `series.name`
  - [x] 3.3.2 在共识生成时，将 `series.name` 直接加入共识结果，不参与 LLM 投票
  - [x] 3.3.3 对前 3 个对象组仅对 `manufacturer`, `country`, `art_style` 进行共识

- [x] 3.4 修改 B 类型系列的处理逻辑
  - [x] 3.4.1 对所有系列级字段（包括 `series.name`）进行共识计算
  - [x] 3.4.2 使用 `fact_description` 任务结果（非 `fact_description_noseries`）

## 4. 测试和验证

- [ ] 4.1 单元测试
  - [ ] 4.1.1 测试共识文件读写工具函数
  - [ ] 4.1.2 测试 `series_consensus.execute_stage()` 的正常和异常情况
  - [ ] 4.1.3 测试字段合并逻辑

- [ ] 4.2 集成测试
  - [ ] 4.2.1 准备 A 类型测试数据集（至少 3 个对象组 + series 样本）
  - [ ] 4.2.2 准备 B 类型测试数据集（至少 3 个对象组）
  - [ ] 4.2.3 验证共识文件生成和字段一致性
  - [ ] 4.2.4 验证断点续传：删除部分输出 JSON，重新运行，确认继承共识
  - [ ] 4.2.5 验证少于 3 组的系列处理
  - [ ] 4.2.6 验证共识文件损坏时的降级处理

- [ ] 4.3 边界情况测试
  - [ ] 4.3.1 输入目录只读时的错误提示
  - [ ] 4.3.2 共识文件格式错误时的降级处理
  - [ ] 4.3.3 所有组的系列级字段都为 `null` 的情况

## 5. 文档更新

- [x] 5.1 更新项目文档
  - [x] 5.1.1 在 `openspec/project.md` 中说明系列级字段的一致性机制
  - [x] 5.1.2 说明 `.series_consensus.json` 的作用和格式

- [x] 5.2 更新配置文档
  - [x] 5.2.1 在 `config/settings.yaml` 注释中说明新增的配置项

- [ ] 5.3 更新用户指南（如果存在）
  - [ ] 5.3.1 说明共识文件的用途和位置
  - [ ] 5.3.2 说明如何强制重新计算共识
  - [ ] 5.3.3 说明系列文件夹的组织建议（高质量图像放在前面）

## 6. 代码审查和优化

- [x] 6.1 代码审查
  - [x] 6.1.1 确保所有新增代码符合项目编码规范（UTF-8、snake_case、类型注解）
  - [x] 6.1.2 确保日志记录清晰、结构化
  - [x] 6.1.3 确保错误处理完善，关键路径有降级逻辑

- [ ] 6.2 性能优化（如需要）
  - [ ] 6.2.1 评估共识生成对管道总执行时间的影响
  - [ ] 6.2.2 考虑是否需要并行处理前 N 组的 VLM 调用

- [x] 6.3 向后兼容性验证
  - [x] 6.3.1 确认对已有输出格式无破坏性变更
  - [x] 6.3.2 确认已有配置文件在不添加新配置项时仍可正常运行

## 7. 部署准备

- [x] 7.1 更新 `tasks.md` 中所有任务为已完成状态
- [ ] 7.2 运行 `openspec validate add-series-level-metadata-consensus --strict` 确认无错误
- [ ] 7.3 准备发布说明，总结新功能和使用注意事项

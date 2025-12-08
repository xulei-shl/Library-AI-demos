# 文章总结流程开发记录
- **日期**: 2025-12-08
- **关联设计**: `docs/design/article_summary_pipeline_20251208.md`

## 内容概述
1. **总结 Agent 实现**  
   - 新增 `ArticleSummaryAgent`（`src/core/analysis/summary_agent.py`），复用 `article_summary` 任务调用统一 LLM 客户端，处理缺失内容提示、结果标准化和错误日志。

2. **总结 Runner 与管线接入**  
   - `ArticleSummaryRunner`（`src/core/article_summary_runner.py`）负责筛选 `filter_pass=True` 且未总结的记录，逐条即时保存，记录最后尝试时间并在失败列表上执行兜底重试。
   - `StorageManager` 扩展 `llm_summary*` 字段，`SubjectBibliographyPipeline` 新增 `run_stage_summary` 与 CLI 参数 `summary`，整体流程可单独触发总结阶段。

3. **任务配置与测试**  
   - `config/llm.yaml` 新增 `article_summary` 任务，启用 Langfuse 追踪、JSON 修复及多 Provider 重试。
   - 新增 `tests/test_article_summary_runner.py`，覆盖待处理筛选、即时保存次数、失败重试与失败持久化等关键路径。测试命令：`PYTHONPATH=. pytest tests/test_article_summary_runner.py`。

## 影响范围
- 核心代码：`src/core/analysis/summary_agent.py`，`src/core/article_summary_runner.py`。
- 基础设施：`src/core/storage.py`、`src/core/pipeline.py`、`config/llm.yaml`。
- 测试：`tests/test_article_summary_runner.py`（新增）。

## 风险与备注
- 依赖新的 `article_summary` LLM 任务配置，请确认相关 API Key 与 Langfuse 环境变量已设置。
- 若需自动串联到完整流程，可在 `run_all_stages` 中追加 summary 阶段，目前保持独立调用。

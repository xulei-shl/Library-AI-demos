# 模块3 - 豆瓣评分流水线断点续跑入库优化方案
## 背景
- 现状：保存 `_partial.xlsx` 时会自动跳过数据库查重阶段，导致流水线末尾的“统一入库（flush）”无法初始化数据库上下文，最终不会写库。
- 需求：在保持断点续跑能力的前提下，确保每次运行结束仍能把“非 DB 来源”的最新结果同步入库。

## 方案分层
1. **方案 A：partial 场景下仍初始化 DB（推荐启用）**  
   - 增加 `--force-db-stage`，或在检测到 partial 时执行“轻量 DB 阶段”：只做查重分类 + `configure_database`，不改 Excel 内容。  
   - 作用：创建 `_row_category_map`，让 DB writer 能够在收尾阶段继续 flush。
2. **方案 B：持久化分类元数据（建议与 A 搭配）**  
   - 首次完成 DB 阶段时将分类结果写入 `runtime/outputs/<excel>_partial.dbmeta.json`。  
   - resume 时即使跳过 DB 阶段，也能从 meta 恢复 `configure_database` 所需信息，避免重复查重并保证 flush 可用。
3. **方案 C：兜底写库开关（默认关闭）**  
   - 当没有 DB 配置/分类时，允许按简化规则临时分类（如“豆瓣数据来源”不含 DB 且状态非 DONE 视为 new）并入库。  
   - 需显式参数开启，日志提示可能的重复写风险。

## 推荐实施顺序
- **优先落地 A + B**：满足“断点续跑 + 统一入库”的主诉求，性能与稳定性兼顾。  
- **C 作为应急开关**：默认关闭，必要时再打开。

## 使用建议
- 断点续跑时，如希望必定入库：  
  - 删除现有 `_partial.xlsx` 重新跑，或  
  - 显式传入 `--force-db-stage`（方案 A），或  
  - 确认存在并加载 `*.dbmeta.json`（方案 B）。  
- 文档提示：保存 partial 时默认行为会改变（不再静默跳过 DB），以保证统一入库可用。

## 2025-11-16 实施记录
- [x] **CLI 新增 `--force-db-stage`**：`douban_main.py` 注入参数到 `DoubanRatingPipelineOptions`，断点续跑时可强制执行完整 DB 查重与写回。
- [x] **ProgressManager 持久化分类元数据**：DB 阶段写入 `<excel>_partial.dbmeta.json`，`finalize_output` 清理 partial/元数据文件，resume 时 `load_db_meta()` 恢复 `_row_category_map` 以支撑统一 flush。
- [x] **DB Stage 轻量模式**：`DoubanDatabaseStage` 根据 `resume_from_partial` / `force_db_stage` 判断是否跳过 Excel 回写，仅恢复分类并保留缓存，避免重复 I/O。
- [x] **流水线恢复逻辑调整**：`DoubanRatingPipeline` 不再静默跳过 DB 阶段，link/API 阶段依赖 `resume_from_partial` 过滤待处理行；完成后全量调用 `flush_row_to_database()`，确保非 DB 来源记录亦可入库。

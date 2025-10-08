Status: Implemented
Date: 2025-10-08
Owner: l3_deep_analysis
Objective / Summary:
- 新增 L3 deep_analysis 模块，实现“三阶段”自动调研工作流：
  1) 从 Excel(根目录 metadata) 读取编号，提取对应实体 JSON 的结构化信息，构造提示，调用 LLM 生成编号_deep.json（含 row_id 与自身 meta）。
  2) 遍历 JSON 中的子问题(subtopics)，分别调用 Jina DeepSearch 与 Dify 检索，将结果与各自 meta 写回；错误写入 metadata 并置该任务结果为 null；支持幂等跳过。
  3) 调用 LLM 基于有效检索结果与初始摘要生成编号_deep.md；默认存在则跳过（可配置覆盖）。

Scope:
- 新增目录/文件：
  - src/core/l3_deep_analysis/
    - excel_loader.py
    - json_schema.py
    - prompt_builder.py
    - planner.py
    - executors/jina_executor.py
    - executors/dify_executor.py
    - orchestrator.py
    - report_writer.py
  - src/prompts/
    - l3_deep_analysis_planning.md
    - l3_deep_analysis_report.md
- 配置更新：
  - config/settings.yaml 中新增 deep_analysis 配置块（见 Detailed Plan → Config）。
- 测试：
  - tests/core/l3_deep_analysis/ 下新增测试用例（Excel解析、JSON写入、幂等策略、API调用mock、报告生成）。

Detailed Plan:
- 输入与定位：
  - excel_loader.py 读取根目录 metadata（支持 .xlsx/.xls），列名“编号”，值作为 row_id；根据 row_id 拼接到 runtime/outputs/{row_id}.json。
- 提取与提示构建：
  - prompt_builder.py 从实体 JSON 中提取：
    - 基础字段：label、type、context_hint（只保留一个代表值）
    - 每实体补充资源：wikipedia-description、wikidata-description、shl_data-description、related_events-label、related_events-description、l3_web_search-content、l3_enhanced_web_retrieval-content、l3_rag_entity_label_retrieval-content、l3_rag_enhanced_rag_retrieval-content（严格按键名）
  - 将上述整合为用户提示文本，供规划 LLM 使用。
- 阶段1（规划 → 编号_deep.json）：
  - planner.py 调用 src/utils/llm_api.py，使用 deep_analysis.planning 配置与系统提示词 src/prompts/l3_deep_analysis_planning.md。
  - 输出 JSON 结构：
    - row_id: string（例如 "2202_001"）
    - summary: string 或 object
    - report_theme: string 或 object
    - subtopics: [ { name, questions: [...] } ... ]
    - meta: { executed_at, status, llm: { model, provider?, endpoint? } }
    - metadata: { 可选，错误聚合 }
  - 幂等：仅当上述必需节点均有值，才跳过；否则执行并覆盖更新。若执行后某节点为 null，应记录并视为跳过（不继续重复）。
- 阶段2（检索执行）：
  - executors/jina_executor.py：
    - 从 .env 读取 JINA_DEEPSEARCH_KEY；base_url 与 endpoint 来自 deep_analysis.jina。
    - 对每个 subtopic 的每个 question 或合并后的查询文本进行请求（根据提示词策略），写入：
      - "jina": { "content": "...", "meta": { status: "success", executed_at, task_type: "web_search", search_query?, search_results_count?, llm_model?, error: null } }
      - 失败：将 "jina": null，同时在 "metadata": { "jina": { executed_at, status: "not_found"/"error", error, task_type, ... } } 记录错误。
    - 幂等：若已存在且 meta.status=success 则跳过。
  - executors/dify_executor.py：
    - 复用 l3_context_interpretation 的 Dify 客户端与重试、速率限制；key 为 env:DIFY_DEEP_INTERPRETATION_KEY；base_url 统一。
    - 输入直接为 subtopic 的问题文本；写入：
      - "dify": { "content": "...", "meta": { executed_at, task_type: "entity_label_retrieval", dify_response_id?, error: null } }
      - 失败：将 "dify": null，并在 "metadata": { "dify": { executed_at, status, error, task_type, dify_response_id? } } 记录。
    - 幂等：若已存在且 meta.status=success 则跳过。
- 阶段3（最终报告）：
  - report_writer.py 调用 src/utils/llm_api.py，使用 deep_analysis.report 配置与系统提示词 src/prompts/l3_deep_analysis_report.md。
  - 汇总 deep.json 中的 summary、report_theme、各 subtopic 的有效检索结果（Jina/Dify）生成 Markdown，文件名 {row_id}_deep.md，保存于与实体 JSON 相同目录。
  - 幂等：默认存在则跳过；若 overwrite_report=true 则覆盖。
- 编排：
  - orchestrator.py 负责：
    - 逐行_id 执行三阶段；日志记录；错误聚合；幂等判断。
    - 允许按 row_id 选择性执行或批量。

Visualization:
```mermaid
flowchart TD
  A[读取Excel: metadata/编号] --> B[定位 runtime/outputs/{row_id}.json]
  B --> C[提取实体基础与补充资源字段]
  C --> D{检查 {row_id}_deep.json 必需节点}
  D -->|齐备| E1[跳过阶段1]
  D -->|缺失| E2[LLM规划生成 {row_id}_deep.json 并写入 meta]
  E2 --> F{遍历 subtopics}
  F --> G{Jina 结果 success?}
  G -->|是| G1[跳过Jina]
  G -->|否或null| G2[Jina调用→写入 content+meta 或 metadata]
  F --> H{Dify 结果 success?}
  H -->|是| H1[跳过Dify]
  H -->|否或null| H2[Dify调用→写入 content+meta 或 metadata]
  F --> I{检查 {row_id}_deep.md 及覆盖策略}
  I -->|存在且不覆盖| J[跳过阶段3]
  I -->|生成/覆盖| K[LLM撰写最终报告→保存 md]
  K --> L[结束]
```

Testing Strategy:

Implementation Notes:
- 阶段2（Dify 检索）已按设计完成并优化：
  - 配置新增：
    - deep_analysis.dify.enabled: true（可关闭整段 Dify 检索）
    - deep_analysis.dify.skip_if_executed: false（默认仅成功时跳过；设为 true 时任何已执行状态均跳过）
  - 执行与幂等：
    - 改为“逐题检索”：对 subtopics.questions 中的每个问题单独请求 Dify
    - 题目级幂等：已存在 success/timeout_recovered 的题默认跳过；若 skip_if_executed=true，则任意已执行状态均跳过
  - 调用与上下文：
    - 复用 DifyEnhancedClient + DifyTimeoutRecovery（src/core/l3_context_interpretation/）
    - 请求映射：label=单题 question，entity_type=subtopic.name，context_hint=summary + report_theme（结构化拼接）
    - 指数退避重试：读取 deep_analysis.dify.retry_policy（max_retries、delay_seconds、backoff_factor）
  - 错误处理与写回：
    - success/timeout_recovered 写入 s["dify"].results 数组（每条含 question/content/meta）
    - not_found/not_relevant/error 不进入 results，统一写入 deep_data.metadata.dify 聚合（含 executed_at/status/error/dify_response_id/question/subtopic）
    - 聚合状态：若至少一条 success/timeout_recovered，则 s["dify"].meta.status=success；否则按 error/not_found 归类
  - 受影响文件：
    - config/settings.yaml（新增 deep_analysis.dify.enabled 与 skip_if_executed）
    - src/core/l3_deep_analysis/executors/dify_executor.py（重写为逐题、结构化上下文、超时恢复与重试）
    - src/core/l3_deep_analysis/orchestrator.py（Dify 阶段改为逐题幂等与聚合写回；与执行器新签名对齐）
  - 兼容性：
    - report_writer 仍以 meta.status == "success" 识别可用 Dify 结果；Jina 流程保持原策略不变
  - 安全性：
    - API Key 从 env 解析，未落盘；日志不输出敏感数据
- 使用 pytest + requests mock：
  - Excel解析：不同编号格式（字符串/数字）映射路径正确。
  - 阶段1幂等：必需节点齐备时跳过；缺失时生成并写入 meta。
  - 阶段2幂等：已有 success 时跳过；错误写 metadata 并置 null。
  - 阶段3：默认跳过；覆盖配置生效。
  - 日志：关键步骤包含 row_id、任务类型、状态。
  - 边界：空实体、缺少补充资源键、网络超时/重试。

Config（settings.yaml 计划新增项）:
deep_analysis:
  enabled: true
  excel_path: "metadata.xlsx"
  id_column: "编号"
  output_dir: "runtime/outputs"
  overwrite_report: false
  planning:
    provider_type: "text"
    temperature: 0.1
    top_p: 0.9
    endpoint: "/chat/completions"
    system_prompt_file: "l3_deep_analysis_planning.md"
  report:
    provider_type: "text"
    temperature: 0.2
    top_p: 0.9
    endpoint: "/chat/completions"
    system_prompt_file: "l3_deep_analysis_report.md"
  jina:
    base_url: "https://deepsearch.jina.ai/v1"
    endpoint: "/chat/completions"
    api_key: "env:JINA_DEEPSEARCH_KEY"
    timeout_seconds: 65
    retry_policy:
      max_retries: 3
      delay_seconds: 2
      backoff_factor: 2.0
  dify:
    base_url: "https://api.dify.ai/v1"
    api_key: "env:DIFY_DEEP_INTERPRETATION_KEY"
    rate_limit_ms: 1000
    timeout_seconds: 65
    timeout_recovery:
      enabled: true
      max_attempts: 3
      delay_seconds: 10
      match_time_window: 120
    retry_policy:
      max_retries: 3
      delay_seconds: 2
      backoff_factor: 2.0

Security Considerations:
- 从 .env 读取 API Key，避免硬编码；不在日志中记录敏感内容。
- 请求超时与重试策略防止阻塞；错误统一 metadata 记录，便于追踪。

Please Approve:
- 若无异议，请批准该提案（Proposal）。批准后我将开始编码，并将文档状态更新为 In Progress。
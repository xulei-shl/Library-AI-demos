Status: Implemented

Objective / Summary
- 将 CLI 入口集中到 src/core/l2_knowledge_linking/main.py
- 使 src/core/l2_knowledge_linking/task_builder.py 仅保留该任务的纯逻辑（构建实体任务列表及内部解析/聚合函数）
- 测试代码统一位于 tests/ 路径，通过 import 引用主逻辑进行验证；测试逻辑不变（仅调整引用入口）

Scope
- 修改：src/core/l2_knowledge_linking/task_builder.py
  - 删除/迁移 CLI 相关代码：_load_settings、_build_excel_io_from_settings、_preview_print、_write_output、main、if __name__ == "__main__"
  - 保留：build_task_list 及其内部私有函数（_parse_keywords_entities、_parse_l1_entities、_add_entity、_safe_json_loads、_clean_json_text、_norm_label）
- 新增/完善：src/core/l2_knowledge_linking/main.py
  - 集中 CLI 能力：_load_settings、_build_excel_io_from_settings、_preview_print、_write_output、main()、if __name__ == "__main__"
  - 从 task_builder import build_task_list
- 测试：tests/core/l2_knowledge_linking/
  - 保持现有 test_entity_extraction.py 的逻辑不变（如需仅微调导入路径）
  - 可补充一个 test_task_builder_cli.py，通过模拟 CLI 参数调用 main.py 的 main()，验证入口迁移后仍可运行（不改变原有测试意图）

Detailed Plan
1. 代码职责调整
   - 将 task_builder.py 中的 CLI 辅助函数与入口迁移到 main.py
   - task_builder.py 仅暴露 build_task_list(xio, settings) 以及内部私有解析/合并函数，不再包含运行入口
2. main.py 入口整合
   - main() 解析命令行参数（--config/--excel/--sheet/--output/--preview）
   - 调用 _load_settings、_build_excel_io_from_settings
   - 调用 task_builder.build_task_list 构建任务列表
   - 调用 _preview_print 展示预览
   - 调用 _write_output 写出 JSON 文件
3. 依赖关系
   - main.py 引用：from .task_builder import build_task_list
   - 保持 utils 模块（excel_io、metadata_context、logger）的现有导入与使用方式
4. 测试适配
   - tests 继续直接针对 build_task_list 进行功能断言（不依赖 __main__）
   - 如需验证 CLI 行为，新增 test_task_builder_cli.py 使用 monkeypatch/sys.argv 方式调用 main.main() 并断言输出文件或控制台预览

Visualization
```mermaid
flowchart TD
    A[命令行启动 main.py] --> B[解析参数 argparse]
    B --> C[_load_settings: 读取配置 YAML/JSON]
    C --> D[_build_excel_io_from_settings: 构造 ExcelIO]
    D --> E[build_task_list(xio, settings) 来自 task_builder]
    E --> F[_preview_print: 控制台预览]
    E --> G[_write_output: 写出 JSON]
    subgraph 任务逻辑: task_builder.py
      E1[_parse_keywords_entities]
      E2[_parse_l1_entities]
      E3[_add_entity 去重合并]
      E4[_safe_json_loads/_clean_json_text/_norm_label]
      E1 --> E3
      E2 --> E3
      E4 --> E1
      E4 --> E2
    end
```

Testing Strategy
- 单元测试（tests/core/l2_knowledge_linking/）
  - 针对 build_task_list：
    - 正常用例：同时提供 keywords_json 与 l1_structured_json，验证抽取、合并、类型优先以及 rows/sources/context_hint
    - 边界用例：空或无效 JSON 文本；缺失路径字段；大小写与空白差异的去重
    - 异常用例：JSON 解析失败时返回 None 并记录 WARNING（通过 logger/捕获）
  - CLI 入口（可选补充）：模拟命令行参数调用 main.main()，验证生成文件路径、预览输出行为
- 测试不依赖 __main__ 入口，全部通过 import 与函数调用进行

Security Considerations
- 不记录敏感信息到日志；日志内容保持中文且包含上下文但不含凭证
- 文件写出路径由配置/参数控制，确保目录创建与异常处理安全

Implementation Notes
- 已将 src/core/l2_knowledge_linking/task_builder.py 纯化，仅保留 build_task_list 及其私有解析/合并函数；移除 CLI 相关的 _load_settings、_build_excel_io_from_settings、_preview_print、_write_output、main、__main__ 入口。
- 已在 src/core/l2_knowledge_linking/main.py 集中新增 task_builder 的 CLI 辅助函数（以 _tb_* 前缀命名），保留原有 run_l2 的 CLI 入口，避免入口冲突。
- 测试：运行 tests/core/l2_knowledge_linking，结果为 3 passed, 1 skipped（跳过原因：Step1 不调用 LLM，按现实现不适用）。
- 与计划差异：为保持最小改动，未新增独立的 task_builder CLI 子命令，仅提供集中到 main.py 的辅助函数供主入口编排。
- 风险与兼容：外部若直接执行 task_builder.py 将不再有 CLI 行为；请改用 main.py 的 CLI 或通过主入口脚本统一编排。

```
批准后执行：
- 更新 task_builder.py（移除 CLI 相关）
- 更新/补充 main.py（集中 CLI 入口）
- 适配/补充 tests
- 文档状态更新为 In Progress → Implemented，并补充 Implementation Notes
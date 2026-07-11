# 01 - 编排器与 CLI

> 路径：`src/core/literature_fm/literature_fm_orchestrator.py`、`src/core/literature_fm/cli.py`

---

## 1. 职责

- **`literature_fm_orchestrator.py`**：`LiteratureFMPipeline` 类，是核心模块的"总指挥"。负责加载配置、驱动 LLM 打标流程、以及 Phase 3 的混合检索编排。
- **`cli.py`**：`LiteratureFMCLI` 类，提供交互式菜单和 argparse 子命令两种入口，把用户操作路由到 Pipeline / 各功能类。

---

## 2. LiteratureFMPipeline

### 2.1 初始化
```python
pipeline = LiteratureFMPipeline()
```
- `_load_config()`：读取 `config/literature_fm.yaml`（`yaml.safe_load`）。若失败直接抛异常。
- 持有 `self.tag_manager = TagManager()`；`self.llm_tagger` 延迟初始化（打标时才创建）。

### 2.2 主要方法
| 方法 | 作用 | 备注 |
|------|------|------|
| `run_llm_tagging() -> bool` | 跑完整 LLM 打标流程（筛选 → 批量打标 → 兜底重试 → 导出） | 受 `llm_tagging.enabled` 控制 |
| `_get_books_to_tag() -> List[Dict]` | 从 `books` 表按 `call_no_prefix / min_douban_rating / required_fields` 筛选待打标书目，并排除已打标 `book_id` | 支持 `max_items` 限制（省钱测试用） |
| `_export_results() -> bool` | 把打标结果导出 Excel，并 `_expand_tags_json` 把 `tags_json` 展开成多列 | `llm_tagging.output.export_to_excel` 控制 |
| `generate_theme_shelf(translated_queries, output_dir, config_path) -> Dict` | **Phase 3 混合检索主流程**（详见第 3 节） | 返回 `{success, themes, total_books, output_file}` |

### 2.3 `generate_theme_shelf` 流程（Phase 3 编排）
对每个 `translated_query` 循环：
1. **去重检查**：`ThemeDeduplicator.get_excluded_book_ids(...)` 得到需排除的 `book_id` 集合。
2. **并行双路召回**：
   - 向量路：`HybridVectorSearcher.search(synthetic_query, filter_conditions, ...)`（受 `use_vector` 控制）。
   - BM25 路：`BM25Searcher.search_with_randomness(search_keywords, randomness, ...)`（受 `use_bm25` 控制）。
3. **RRF 融合**：`RRFFusion.merge(vector_results, bm25_results)`；若只有单路则直接采用该路。
4. **[可选] 重排序**：`CrossEncoderReranker.rerank(...)`（受 `reranker.enabled` 控制）。
5. **截断 + 保存**：取 `final_top_k`（默认 30），`ThemeDeduplicator.save_recommendation(...)` 写推荐历史。
6. 最后 `ThemeExporter.export_theme_batch(all_results)` 导出 Excel。

> 配置来源：`config/literature_fm_vector.yaml` 的 `default / database / bm25 / rrf / reranker` 段。

---

## 3. LiteratureFMCLI

### 3.1 交互式菜单（`run_interactive`）
菜单项 → 处理函数：
- `1` LLM 打标 → `_cmd_llm_tagging`
- `2` 生成策划主题 → `_cmd_theme_generation`
- `3` 查询意图转换 → `_cmd_query_translation`（支持 Excel/JSON/单主题）
- `4` 情境主题检索 → `_cmd_theme_shelf`（自然语言或 JSON 文件）
- `5` 数据库向量化 → `_cmd_vectorize`（状态/清空/重新向量化）
- `6` 候选图书 LLM 筛选 → `_cmd_candidate_filter`
- `7` 生成卷首导读 → `_cmd_prologue_generator`
- `0` 退出

### 3.2 argparse 子命令（`main`）
| 子命令 | 参数 | 路由 |
|--------|------|------|
| `tag` | — | `_cmd_llm_tagging` |
| `theme-gen` | `--random` / `--direction` / `--count` | `_generate_themes` |
| `query-trans` | `--excel` / `--json` / `--status-col` / `--status-val` | `_translate_from_*` |
| `shelf` | `--theme` / `--query-json` | `_theme_shelf_from_text_direct` / `_theme_shelf_from_json_file` |
| `vectorize` | — | `_cmd_vectorize` |
| （缺省） | — | `run_interactive` |

### 3.3 注意事项
- CLI 通过 `self.pipeline.config` 读取各功能开关；很多功能在未 `enabled` 时会打印提示并直接返回（不会报错退出）。
- `_run_hybrid_search` 是 CLI 与 Pipeline 的桥接点：把 `translated_queries` 交给 `pipeline.generate_theme_shelf`。

---

## 4. 交接要点
- 修改"整条链路默认行为"应改 `literature_fm_orchestrator`，不要在各功能类里改流程。
- `generate_theme_shelf` 同时被 CLI 的 `shelf` 与 API 之外的批处理调用，是检索编排的唯一真源（API 模块在 `search_service.py` 内自行编排了简化版，二者应保持一致）。
- 根目录路径：`root_dir = Path(__file__).absolute().parent.parent.parent.parent`，确保 `sys.path` 含项目根。

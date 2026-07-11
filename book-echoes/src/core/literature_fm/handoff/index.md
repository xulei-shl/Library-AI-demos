# 纯文学模块 Handoff 文档总索引

> 模块：Module 8 - Literature FM（文学FM / 文学情境推荐）
> 适用范围：`src/core/literature_fm/` 与 `src/core/literaturefm-api/`
> 文档版本：v1.0　最后更新：2026-07-10

---

## 0. 这个模块是做什么的

纯文学模块负责把馆藏文学图书按"阅读情境"进行组织与推荐。整条链路可以概括为：

1. **打标（Tagging）**：用 LLM 给每本书打上 5 个维度的文学标签（阅读情境 / 阅读体感 / 文本质感 / 时空氛围 / 情绪基调）。
2. **向量化（Vectorize）**：把打标结果 + 豆瓣元数据嵌入 ChromaDB，供语义检索使用；同时构建 BM25 词典索引。
3. **策划（Planning）**：用 LLM 生成"文学策划主题"（如"冬夜独处 · 暖灯下的一杯热可可"）。
4. **转换（Translate）**：把自然语言主题翻译成结构化检索条件（过滤条件 + 关键词 + 合成查询词）。
5. **检索（Retrieve）**：向量检索 + BM25 检索双路召回，经 RRF 融合（可选 CrossEncoder 重排序）产出候选书单。
6. **精修（Refine）**：对候选书单做 LLM 二次筛选、去重、生成卷首导读，最终导出 Excel 书单。

服务化的部分（`literaturefm-api`）把"检索"这一步封装成 FastAPI，向上层（前端 / 其他模块）提供 `POST /api/literary/search` 与 `POST /api/literary/batch-search`。

---

## 1. 目录结构

```
src/core/literature_fm/                 # 核心逻辑（批处理 / CLI / 检索算法）
├── __init__.py                         # 模块导出
├── cli.py                              # 统一 CLI 入口（交互式菜单 + 子命令）
├── literature_fm_orchestrator.py       # 主流程编排器（Pipeline）
├── llm_tagger.py                       # LLM 打标器
├── tag_manager.py                      # 标签表 CRUD
├── db_init.py                          # 建表 / 升级（literary_tags、推荐历史）
├── db_vectorizer.py                    # 批量向量化（写 ChromaDB）
├── import_literary_tags.py             # CSV/XLSX 标签导入工具
├── theme_generator.py                  # 文学策划主题生成器
├── query_translator.py                 # 查询意图转换器
├── vector_searcher.py                  # 基础向量检索器（ChromaDB）
├── hybrid_vector_searcher.py           # 增强向量检索器（过滤条件）
├── bm25_searcher.py                    # BM25 全文检索器
├── rrf_fusion.py                       # RRF 融合器
├── cross_encoder_reranker.py           # CrossEncoder 重排序器（可选）
├── theme_deduplicator.py               # 推荐去重器
├── theme_exporter.py                   # 结果导出器（Excel）
├── candidate_filter.py                 # 候选图书 LLM 筛选（Phase 3.5）
├── prologue_generator.py               # 卷首导读生成（Phase 3.6）
├── seatch_test.py                      # 端到端冒烟测试脚本
├── 使用说明.md                          # （已过时，见 检索架构说明.md）
└── 检索架构说明.md                      # 检索子链路架构详解

src/core/literaturefm-api/              # 检索服务化（FastAPI）
├── main.py                             # FastAPI 应用入口
├── config.py                           # 配置加载（literature_fm_vector.yaml）
├── models/requests.py                  # 请求 Pydantic 模型
├── models/responses.py                 # 响应 Pydantic 模型
├── services/search_service.py          # 检索服务（复用核心检索组件）
├── tests/manual_test.py                # 手动测试脚本
└── search-api-docs/图书检索API接口文档.md  # 接口文档
```

---

## 2. 模块文档导航（Handoff 子文档）

| 文档 | 覆盖内容 | 关键文件 |
|------|----------|----------|
| [01-编排器与CLI.md](./01-编排器与CLI.md) | Pipeline 总入口、CLI 菜单、各 Phase 路由 | `literature_fm_orchestrator.py`, `cli.py` |
| [02-打标流水线.md](./02-打标流水线.md) | LLM 打标、标签表管理、建表、向量化、CSV 导入 | `llm_tagger.py`, `tag_manager.py`, `db_init.py`, `db_vectorizer.py`, `import_literary_tags.py` |
| [03-主题生成.md](./03-主题生成.md) | 文学策划主题生成（LLM + Excel/JSON 导出） | `theme_generator.py` |
| [04-查询意图转换.md](./04-查询意图转换.md) | 主题 → 过滤条件/关键词/合成查询 | `query_translator.py` |
| [05-检索核心.md](./05-检索核心.md) | 向量检索、混合过滤检索、BM25 检索 | `vector_searcher.py`, `hybrid_vector_searcher.py`, `bm25_searcher.py` |
| [06-融合与重排序.md](./06-融合与重排序.md) | RRF 融合、CrossEncoder 重排序 | `rrf_fusion.py`, `cross_encoder_reranker.py` |
| [07-去重与导出.md](./07-去重与导出.md) | 推荐历史去重、Excel 书单导出 | `theme_deduplicator.py`, `theme_exporter.py` |
| [08-候选筛选与导读.md](./08-候选筛选与导读.md) | 候选书单 LLM 二次筛选、卷首导读生成 | `candidate_filter.py`, `prologue_generator.py` |
| [09-检索API服务.md](./09-检索API服务.md) | FastAPI 服务、配置、请求/响应模型 | `literaturefm-api/` 全部 |
| [10-数据库与表设计.md](./10-数据库与表设计.md) | 三张表设计：`books`/`literary_tags`/`literature_recommendation_history`、状态机、访问入口 | `db_init.py`, `tag_manager.py`, `db_vectorizer.py`, `database_manager.py` |

---

## 3. 关键入口与运行方式

### 3.1 批处理 / 交互式（核心模块）

```bash
# 交互式菜单（推荐新手从这里进入）
python src/core/literature_fm/cli.py
python src/core/literature_fm/cli.py interactive        # 同上

# 子命令
python src/core/literature_fm/cli.py tag               # LLM 打标
python src/core/literature_fm/cli.py theme-gen --random --count 5
python src/core/literature_fm/cli.py query-trans --excel themes.xlsx
python src/core/literature_fm/cli.py shelf --theme "冬日暖阳，窝在沙发里阅读"
python src/core/literature_fm/cli.py vectorize
```

### 3.2 检索服务（API 模块）

```bash
cd src/core/literature_fm/literaturefm-api
uvicorn main:app --reload --port 8001
# 文档： http://localhost:8001/docs
```

### 3.3 端到端冒烟测试

```bash
python src/core/literature_fm/seatch_test.py
```

---

## 4. 配置与数据依赖

| 资源 | 路径 | 说明 |
|------|------|------|
| 主配置（打标/主题/转换/筛选） | `config/literature_fm.yaml` | 被 `literature_fm_orchestrator` 与 `cli` 加载 |
| 检索配置（向量/BM25/RRF/Reranker） | `config/literature_fm_vector.yaml` | 被 `literaturefm-api/config.py` 及检索组件加载 |
| 标签词表 | `config/literary_tags_vocabulary.yaml` | 5 维标签的候选值，注入 LLM prompt |
| LLM 配置 | `config/llm.yaml` | `UnifiedLLMClient` 的模型/provider |
| 业务库 | `runtime/database/books_history.db` | `books` 表（书目元数据）+ `literary_tags` 表（标签）+ `literature_recommendation_history` 表 |
| 向量库 | `runtime/vector_db/literature_fm/` | ChromaDB 持久化目录 |
| 输出 | `runtime/outputs/theme_shelf/`、`runtime/outputs/literary_tagging/` | Excel 书单、打标结果 |

> 路径约定：核心与 API 模块均通过 `Path(__file__).absolute().parent.parent.parent.parent` 把项目根目录（`book-echoes/`）加入 `sys.path`，因此内部一律使用绝对导入 `src.core.literature_fm.*` 与 `src.utils.*`。

---

## 5. 端到端数据流

```
books 表
  │ (LLM 打标)
  ▼
literary_tags 表  ──向量化──▶  ChromaDB  (literature_fm_contexts 集合)
  │                              ▲
  │                              │ 向量检索
  │ (BM25 索引)                  │
  ▼                              │
BM25Searcher ───────────────────┘
  │
theme_generator (策划主题)
  │
  ▼
query_translator (→ filter_conditions / search_keywords / synthetic_query)
  │
  ├─► HybridVectorSearcher  ─┐
  ├─► BM25Searcher          ─┤─► RRFFusion ─► [CrossEncoderReranker] ─► ThemeExporter ─► Excel
  └─► ThemeDeduplicator(排除) ┘
                                          │
                              candidate_filter (LLM 二次筛选) → prologue_generator (卷首导读)
```

检索服务化（`literaturefm-api`）复用上面虚线框内的 `HybridVectorSearcher / BM25Searcher / RRFFusion / CrossEncoderReranker`，对外暴露 HTTP 接口，不负责打标与精修。

---

## 6. 交接要点（新人必读）

1. **两套配置**：`literature_fm.yaml`（批处理）与 `literature_fm_vector.yaml`（检索/API）作用不同，改检索参数要改后者。
2. **5 维标签体系**是贯穿全链路的核心数据契约：`reading_context / reading_load / text_texture / spatial_atmosphere / emotional_tone`。任何与标签相关的修改都要同步核对 `literary_tags_vocabulary.yaml`。
3. **去重依赖历史表**：`theme_deduplicator` 会排除历史已推荐书目；调试"为什么某本书没出来"先查 `literature_recommendation_history`。
4. **API 与 CLI 共用检索组件**：不要在 API 里重写检索逻辑，改动应落在 `src/core/literature_fm/` 的检索组件内。
5. **检索架构的细节**：已有 [检索架构说明.md](../检索架构说明.md) 对 Step1~Step5、RRF、动态阈值、随机性有深入说明，本文集不再重复，请交叉阅读。

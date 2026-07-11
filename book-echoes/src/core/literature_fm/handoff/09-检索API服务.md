# 09 - 检索 API 服务

> 路径：`src/core/literaturefm-api/`
> 作用：把"混合检索"这一步服务化为 FastAPI，向上层提供 HTTP 接口

---

## 1. 模块结构

```
literaturefm-api/
├── main.py                 # FastAPI 应用入口（lifespan 初始化服务）
├── config.py               # 加载 literature_fm_vector.yaml + 路径解析
├── models/requests.py      # SearchRequest / BatchSearchRequest / FilterCondition
├── models/responses.py     # SearchResponse / BookResult / 元数据 / 统计
├── services/search_service.py  # LiterarySearchService（复用核心检索组件）
└── tests/manual_test.py    # 手动测试
```

启动：
```bash
cd src/core/literature_fm/literaturefm-api
uvicorn main:app --reload --port 8001
# Swagger: http://localhost:8001/docs
```

---

## 2. main.py — 应用入口

- `lifespan`：启动时 `service = LiterarySearchService()` 全局单例；关闭时清理。
- 路由：
  - `GET /`：服务信息（名称/版本/端点列表）。
  - `GET /health`：健康检查。
  - `POST /api/literary/search`：单主题检索 → `service.search(request)`。
  - `POST /api/literary/batch-search`：批量检索 → `service.batch_search(...)`（先把 Pydantic 查询转成 dict 列表）。
  - 全局异常处理器：未捕获异常统一返回 500。
- 异常映射：校验失败/值错误 → 400；其他 → 500。

---

## 3. config.py — 配置

- `load_config()`：读 `config/literature_fm_vector.yaml`；不存在则回退 `get_default_config()`。
- `_resolve_paths`：把配置里的相对路径（`database.path` / `vector_db.persist_directory`）解析为绝对路径（基于项目根）。
- `get_default_config()`：内置默认（chromadb + BAAI/bge-m3 + BM25/默认开启 + reranker 关闭 + final_top_k=30）。

> API 与核心批处理**共用** `literature_fm_vector.yaml`，改检索行为改这一份即可。

---

## 4. services/search_service.py — `LiterarySearchService`

**复用**核心检索组件（绝对导入）：
`HybridVectorSearcher / BM25Searcher / RRFFusion / VectorSearcher / CrossEncoderReranker`。

- `__init__`：按配置初始化各检索器（受 `default.use_vector / use_bm25`、 `reranker.enabled` 控制）。
- `search(request) -> Dict`：
  1. `_convert_filter_conditions` 把 Pydantic 条件转 dict。
  2. 向量路：`vector_searcher.search(synthetic_query, filter_conditions, top_k, min_confidence)`。
  3. BM25 路：`bm25_searcher.search_with_randomness(keywords, top_k, randomness)`。
  4. RRF 融合（任一路为空则退化为另一路）。
  5. 可选重排序（`enable_rerank`）。
  6. 截断 `top_k` → `_format_response`。
- `batch_search(queries, top_k, response_detail, enable_rerank)`：循环构造 `SearchRequest` 调 `search`，聚合 `results / metadata_list`。
- `_format_response`：
  - `basic`：书籍基础信息 + 分数。
  - `standard`：+ `tags_json` + 应用的过滤条件。
  - `rich`：+ `retrieval_stats`（vector/bm25/final 计数）。

**与 `literature_fm_orchestrator.generate_theme_shelf` 的关系**：两者编排逻辑高度一致，但 API 版**不含**去重（`ThemeDeduplicator`）与历史保存，也不导出 Excel，只返回 JSON。改动检索算法须同步两处。

---

## 5. 请求/响应模型（models/）

- `FilterCondition`：`field / values / operator`（operator ∈ MUST/SHOULD/MUST_NOT）。
- `SearchRequest`：`filter_conditions / search_keywords / synthetic_query / top_k / response_detail / enable_rerank / bm25_randomness / min_confidence`。
- `BatchSearchRequest`：`queries / top_k / response_detail / enable_rerank`。
- `BookResult`：`book_id / title / author / call_no / vector_score / bm25_score / rrf_score / sources / tags_json`。
- 过滤条件字段候选值（接口文档 `search-api-docs/图书检索API接口文档.md`）：
  `reading_context / reading_load / text_texture / spatial_atmosphere / emotional_tone`。

---

## 6. 交接要点
- API 不重复实现检索算法，只做"编排 + HTTP 适配 + 响应格式化"。新增检索能力应改核心模块，再在此引用。
- API 默认**不写推荐历史、不去重**——若上游需要去重，需自行调用 `ThemeDeduplicator` 或在 service 内接入。
- 路径约定：API 把自身目录加入 `sys.path` 以导入 `models / config`，同时把项目根加入以导入 `src.core.*`。
- 接口完整字段说明见 `search-api-docs/图书检索API接口文档.md` 与 `/docs`。

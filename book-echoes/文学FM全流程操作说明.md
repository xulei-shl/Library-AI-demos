# 文学FM全流程操作说明

## 一、数据过滤

### 1.1 配置说明

`config/literature_fm.yaml` 的 `input`、`filters`、`output` 部分即为数据过滤配置。

**输入配置（input）**
- `excel_files`: 支持文件路径或目录路径；目录路径配合 `scan_directories: true` 可批量扫描。
- `required_columns`: 验证输入的 Excel 必须包含的列名。
- `scan_directories`: 是否扫描目录中的 Excel 文件。

**过滤规则配置（filters）**
- `call_number_rules`: 索书号规则文件路径。
- `title_keywords_rules`: 题名关键词规则文件路径；留空则不启用题名过滤。
- `field_mapping`: 支持不同 Excel 的列名差异映射。
- `null_handling`: 空值处理策略，`filter` 表示过滤，`keep` 表示保留。
- `logic`: 过滤逻辑，`OR` 表示满足任一规则即过滤，`AND` 表示同时满足。

**输出配置（output）**
- `output_dir`: 筛选结果输出目录。
- `filename_template`: 文件名模板，支持时间戳。
- `add_filter_reason`: 是否添加过滤原因列。
- `merge_passed_data`: 是否合并所有符合条件的数据。
- `add_source_file_column`: 合并时是否添加来源文件列。

### 1.2 运行命令

```bash
# 使用默认配置
python src/scripts/data_filter.py

# 使用本配置文件执行文学数据过滤
python src/scripts/data_filter.py --config config/literature_fm.yaml

# 覆盖输出目录
python src/scripts/data_filter.py --config config/literature_fm.yaml --output-dir runtime/outputs/literature_LiteratureFM_filtered

# 覆盖输入文件（单个或列表）
python src/scripts/data_filter.py --config config/literature_fm.yaml --files data/new/2025/shang/file1.xlsx data/new/2025/shang/file2.xlsx

# 开启 DEBUG 日志查看详细过程
python src/scripts/data_filter.py --config config/literature_fm.yaml --log-level DEBUG
```

### 1.3 输出说明

运行时会在 `runtime/outputs/literature_LiteratureFM_filtered/` 下生成：
- `数据筛选结果_YYYYMMDD_HHMMSS.xlsx` — 符合条件的数据（合并后）。
- `被过滤数据_YYYYMMDD_HHMMSS.xlsx` — 被过滤的数据（含"过滤原因"列）。
- `过滤报告_YYYYMMDD_HHMMSS.txt` — 详细的过滤统计报告。

### 1.4 参考文档

- 过滤规则语法：`config/filters/literature_clc.txt`
- 本步骤详细说明：[src/scripts/data_filter.py](../src/scripts/data_filter.py)

---

## 二、统一入口

`src/core/literature_fm/cli.py` 为文学FM模块的统一 CLI 入口，支持交互式菜单和子命令两种方式。

### 2.1 交互式菜单

```bash
python src/core/literature_fm/cli.py
```

使用后会进入交互式菜单，可选择 1-7 功能：
1. LLM 打标 (Phase 2)     — `tag`
2. 生成策划主题 (Phase 2.5) — `theme-gen`
3. 查询意图转换 (Phase 2.6) — `query-trans`
4. 情境主题检索 (Phase 3)   — `shelf`
5. 数据库向量化            — `vectorize`
6. 候选图书筛选 (Phase 3.5) — `candidate-filter`
7. 生成卷首导读 (Phase 3.6) — `prologue`

### 2.2 子命令

```bash
# 生成主题（随机）
python src/core/literature_fm/cli.py theme-gen --random --count 5

# 生成主题（基于关键词）
python src/core/literature_fm/cli.py theme-gen --direction "冬日治愈" --count 3

# 查询意图转换（Excel）
python src/core/literature_fm/cli.py query-trans --excel themes.xlsx

# 查询意图转换（JSON）
python src/core/literature_fm/cli.py query-trans --json themes.json

# LLM 打标
python src/core/literature_fm/cli.py tag

# 情境主题检索（自然语言主题）
python src/core/literature_fm/cli.py shelf --theme "冬日暖阳，窝在沙发里阅读"

# 情境主题检索（JSON 文件）
python src/core/literature_fm/cli.py shelf --query-json themes.json

# 数据库向量化
python src/core/literature_fm/cli.py vectorize
```

---

## 三、Phase 2 — LLM 打标

### 3.1 功能概述

对数据库中满足条件的已过滤文学书目进行 LLM 情境标签打标。

### 3.2 运行方式

交互式菜单选 `1`，或子命令：
```bash
python src/core/literature_fm/cli.py tag
```

### 3.3 关键配置

`config/literature_fm.yaml` 中 `llm_tagging` 部分：
- `enabled`: 是否启用
- `max_items`: 限制处理数量（测试用）
- `vocabulary_file`: 标签词表配置路径
- `filter_conditions`: 筛选条件（索书号前缀、最低评分、必填字段）
- `batch_processing.batch_size`: 每批处理数量
- `retry_strategy`: 失败重试策略

### 3.4 参考文档

详细说明：[src/core/literature_fm/使用说明.md](./src/core/literature_fm/使用说明.md)

---

## 四、Phase 2.5 — 生成策划主题

### 4.1 功能概述

基于随机或关键词，由 LLM 批量生成文学策划主题（名称、副标题、情境描述、预期氛围）。

### 4.2 运行方式

交互式菜单选 `2`，或子命令：
```bash
python src/core/literature_fm/cli.py theme-gen --random --count 5
```

### 4.3 关键配置

`config/literature_fm.yaml` 中 `theme_generation` 部分：
- `enabled`: 是否启用
- `default_count`: 默认生成数量
- `output`: 输出目录与文件名模板

---

## 五、Phase 2.6 — 查询意图转换

### 5.1 功能概述

将文学策划主题（名称/副标题/描述/氛围）转换为结构化检索条件，包括：
- 过滤条件（reading_context、reading_load、text_texture、spatial_atmosphere、emotional_tone）
- BM25 检索关键词
- 向量检索合成查询词

### 5.2 运行方式

交互式菜单选 `3`，或子命令：
```bash
python src/core/literature_fm/cli.py query-trans --excel themes.xlsx
python src/core/literature_fm/cli.py query-trans --json themes.json
```

---

## 六、Phase 3 — 情境主题检索

### 6.1 功能概述

基于转换后的查询，同时执行向量语义检索与 BM25 关键词检索，再经 RRF 融合、去重、可选重排序，最终输出主题书槽。

检索架构包含：
- `QueryTranslator`：查询意图转换
- `HybridVectorSearcher`：向量语义检索 + 结构化过滤
- `BM25Searcher`：关键词字面匹配（支持随机性采样）
- `RRFFusion`：RRF 融合算法合并多路召回
- `CrossEncoderReranker`：可选重排序
- `ThemeDeduplicator`：历史推荐去重

### 6.2 运行方式

交互式菜单选 `4`，或子命令：
```bash
# 从自然语言主题自动转换并检索
python src/core/literature_fm/cli.py shelf --theme "冬日暖阳，窝在沙发里阅读"

# 从 JSON 文件加载已转换的查询并检索
python src/core/literature_fm/cli.py shelf --query-json themes.json
```

### 6.3 关键配置

- `config/literature_fm.yaml` 中 `theme_generation` 部分
- 检索详细配置：`config/literature_fm_vector.yaml`

### 6.4 参考文档

检索架构与组件详解：[src/core/literature_fm/检索架构说明.md](./src/core/literature_fm/检索架构说明.md)

模块使用说明：[src/core/literature_fm/使用说明.md](./src/core/literature_fm/使用说明.md)

---

## 七、Phase 3.5 — 候选图书 LLM 筛选

### 7.1 功能概述

对主题检索得到的候选图书，按 Excel 中的人工评选状态，用 LLM 筛选确定真正进入推荐的图书，并分组输出。

### 7.2 运行方式

交互式菜单选 `6`，输入候选图书 Excel 文件路径。

### 7.3 关键配置

`config/literature_fm.yaml` 中 `candidate_filter` 部分：
- `enabled`: 是否启用
- `excluded_sheets`: 排除的 sheet 名称
- `grouping.group_size`: 每组图书数量
- `grouping.shuffle`: 是否随机打乱后分组
- `llm.task_name`: 对应 LLM 任务名（`literary_reranking`）

---

## 八、Phase 3.6 — 生成卷首导读

### 8.1 功能概述

基于候选图书和主题信息，由 LLM 生成主题的卷首导读文章。

### 8.2 运行方式

交互式菜单选 `7`，输入候选图书 Excel 文件路径。

### 8.3 关键配置

`config/literature_fm.yaml` 中 `prologue_generator` 部分：
- `enabled`: 是否启用
- `approval_column`: 人工评选列名
- `approval_value`: 通过的值
- `llm.task_name`: 对应 LLM 任务名（`literary_writer`）

---

## 九、附录 A — 文学图书检索 API

### A.1 服务简介

基于向量 + BM25 的混合检索 FastAPI 服务，支持结构化过滤条件。对外提供 RESTful HTTP 接口。

### A.2 启动方式

```bash
cd src/core/literature_fm/literaturefm-api
uvicorn main:app --reload --port 8001
```

### A.3 接口文档

启动后访问：`http://localhost:8001/docs`（Swagger / OpenAPI）

主要接口：
- `POST /api/literary/search` — 单主题检索
- `POST /api/literary/batch-search` — 批量主题检索

### A.4 参考文档

详细文档：[src/core/literaturefm-api/README.md](./src/core/literaturefm-api/README.md)

# 模块3 - 豆瓣评分与ISBN获取流水线

## 概述

本模块包含两条核心流水线：
1.  **FOLIO ISBN 流水线**: 从 FOLIO 系统异步获取图书的 ISBN 号。
2.  **豆瓣评分流水线**: 基于 ISBN，通过**三阶段（数据库查重、豆瓣链接采集、豆瓣API填充）** 的方式获取豆瓣评分和信息。

这两条流水线可以独立运行，也可以通过 `full` 命令串联，实现从条码到完整豆瓣信息的全自动化处理。系统支持断点续跑、可配置的速率限制和详细的日志记录。

## 核心特性

### 1️⃣ FOLIO ISBN 流水线 (`isbn`)
-   **异步并发**: 基于 `asyncio` 和 `aiohttp` 实现高并发请求，性能卓越。
-   **智能配置**: 根据数据量自动选择或手动指定（保守、平衡、激进）并发策略。
-   **断点续存**: 定期保存进度，支持从中断处继续。

### 2️⃣ 豆瓣评分流水线(`douban-rating`)
-   **阶段化执行**：数据库查重 → 链接采集 → API 填充三个步骤，可按需跳过或强制执行。
-   **数据库缓存**：对已获取的数据进行缓存，避免重复请求，支持过期刷新。
-   **Playwright 支持**：使用 Playwright 模拟浏览器搜索链接，有效应对反爬。
-   **增量报告**：生成详细 TXT/Markdown 报告，记录每次处理结果。
-   **链接采集写回评分**：链接阶段从搜索结果页解析并写入 `豆瓣评分`、`豆瓣评价人数`；若命中“评价人数不足/暂无评价”则仅写入链接。
-   **主题评分统计**：链接阶段完成后会根据索书号前缀生成“评分 × 主题”Markdown 报告，辅助人工复核。
-   **动态阈值过滤**：新增“链接已获取”中间状态，通过 `DynamicThresholdFilter`（评论人数黄金区间 + 评分分位）筛出候选后才标记为“待补API”，只有这些记录才会进入 Subject API 阶段。
-   **候选标记列**：额外写回 `候选状态`（可配置列名），所有命中动态阈值的记录都会标记为“候选”，即使状态已“完成”也能在报告中突出出来。
-   **API 仅处理待补**：Subject API 仅处理状态列标记为“待补API”的记录，评分过滤已经在前序的动态阈值环节完成。
-   **阶段交互提示**：链接阶段完成后可选择“继续 API / 暂停”；非交互环境默认继续，可通过 `DoubanRatingPipelineOptions.prompt_post_link_action=False` 全程无提示。
-   **DB 阶段开关**：`--skip-db-stage` 可关闭数据库回写，仅跑链接/API；`--force-db-stage` 在断点续跑时也会强制完整执行 DB 阶段，覆盖轻量模式。
-   **统一入库**：流程结束后，无论是否调用 API，都会将本次处理的数据增量写入数据库；断点续跑默认以“轻量模式”跳过重复回写（DB 阶段仅恢复分类/缓存，不覆写 Excel），但收尾的数据库 flush 仍会写入本轮新增/更新，如需完整刷写请显式带上 `--force-db-stage`。

> Excel 状态列关键节点：`待补链接` → `链接已获取` → `待补API` → `完成`；动态过滤只会把满足条件的记录推进到“待补API”。若记录已经“完成”，则保持状态不变，但会在 `候选状态` 中写上“候选”。

## 使用方法

### 命令行接口 (CLI)

主程序入口为 `src/core/douban/douban_main.py`。

#### 1. 仅运行 FOLIO ISBN 获取
此命令用于为 Excel 文件中的图书条码补充 ISBN 号。

```bash
python src/core/douban/douban_main.py isbn --excel-file "借阅数据.xlsx"
```

#### 2. 运行豆瓣评分流水线
此命令负责从 ISBN 获取豆瓣信息，包含三个内部阶段。

```bash
# 运行完整的豆瓣评分流水线 (数据库查重 -> 链接采集 -> API填充)
python src/core/douban/douban_main.py douban-rating --excel-file "借阅数据.xlsx"

# **跳过特定阶段** (通过 --skip-* 参数)
# 示例：只运行链接采集阶段 (跳过数据库和API阶段)
python src/core/douban/douban_main.py douban-rating --excel-file "借阅数据.xlsx" --skip-db-stage --skip-subject-stage

# 示例：只运行API填充阶段 (假设链接已存在)
python src/core/douban/douban_main.py douban-rating --excel-file "借阅数据.xlsx" --skip-db-stage --skip-link-stage

# 示例：从 partial 继续时强制完整 DB 回写
python src/core/douban/douban_main.py douban-rating --excel-file "借阅数据.xlsx" --force-db-stage
```

执行说明：
- 链接采集阶段会写入 `豆瓣链接`、`豆瓣评分`、`豆瓣评价人数` 并生成“主题评分 + 动态阈值参考”Markdown 报告。
- 链接阶段完成后立即执行动态阈值过滤：满足评论人数黄金区间且评分达标的记录被标记为“待补API”，其余保持“链接已获取”。
- Subject API 只会处理“待补API”行（由前序动态阈值筛出的记录），不再额外根据评分阈值二次过滤。
- 链接阶段结束后 CLI 会提示是继续执行 Subject API 还是暂时中止（非交互环境自动继续，可配置关闭）。
- 所有阶段完成后执行一次统一入库，默认的“轻量模式”仅在 DB 阶段恢复分类/缓存，不向 Excel 重写历史数据，但最终的数据库 flush 仍会把本轮新增/更新写入数据库；如需重新刷写 DB 并同步 Excel，请加 `--force-db-stage`。

#### 3. 运行完整的串行流程
此命令将自动依次执行 FOLIO ISBN 获取和豆瓣评分两个完整流程，实现端到端自动化。

```bash
# 串行运行：FOLIO ISBN 获取 -> 豆瓣评分流水线
python src/core/douban/douban_main.py full --excel-file "借阅数据.xlsx"
```

### 常用命令行参数

| 参数 | 命令 | 说明 | 默认值 |
|---|---|---|---|
| `--excel-file` | `isbn`, `douban-rating`, `full` | **必需**，指定要处理的 Excel 文件路径。 | - |
| `--config-name` | `isbn`, `douban-rating`, `full` | 指定性能配置方案（如 `balanced`, `aggressive`）。 | `balanced` |
| `--disable-database` | `isbn`, `douban-rating`, `full` | 禁用数据库缓存，所有数据都重新爬取。 | `False` |
| `--force-update` | `isbn`, `douban-rating`, `full` | 强制刷新数据库中的所有数据，忽略过期时间。 | `False` |
| `--test` | `isbn` | 测试模式，仅处理文件的前5条记录。 | `False` |
| `--skip-db-stage` | `douban-rating` | 跳过豆瓣流程的“数据库查重”阶段。 | `False` |
| `--force-db-stage` | `douban-rating`, `full` | 断点续跑时也执行完整数据库阶段，覆盖轻量模式 | `False` |
| `--skip-link-stage` | `douban-rating` | 跳过豆瓣流程的“链接采集”阶段。 | `False` |
| `--skip-subject-stage` | `douban-rating` | 跳过豆瓣流程的“API填充”阶段。 | `False` |


### 配置文件
详细的并发数、延迟、重试次数、API 地址等参数可在 `config/setting.yaml` 中配置：
```yaml
douban:
  link_resolver:
    max_concurrent: 2
    headless: false
    # ... 其他链接解析器配置
  subject_api:
    base_url: "https://m.douban.com/rexxar/api/v2/subject"
    max_concurrent: 5
    # ... 其他 API 客户端配置
  analytics:
    theme_rating:
      min_sample_size: 30
      review_lower_percentile: 40
      review_upper_percentile: 80
      rating_percentile_large: 75
      top_n_per_category: 20
      category_min_scores:
        I: 8.0
        default: 7.5
      # ↑ 这些参数直接驱动 DynamicThresholdFilter 的筛选与 Markdown 报告
  database:
    db_path: "runtime/database/books_history.db"
    # ... 其他数据库配置
```


字段写回（Excel列名来源于 `fields_mapping.douban`）：
- `url` → `豆瓣链接`
- `rating` → `豆瓣评分`
- `rating_count` → `豆瓣评价人数`
- 状态列（默认 `处理状态`）将按进度写入 `待补链接 / 链接已获取 / 待补API / 完成`
- `candidate_column`（默认 `候选状态`）会在命中动态阈值时写入“候选”，用于标记推荐书目

## 编程接口

#### 独立调用流水线
```python
from src.core.douban.pipelines import (
    FolioIsbnPipeline, FolioIsbnPipelineOptions,
    DoubanRatingPipeline, DoubanRatingPipelineOptions
)

# 1. 运行 Folio ISBN 流程
folio_pipeline = FolioIsbnPipeline()
folio_opts = FolioIsbnPipelineOptions(excel_file="借阅数据.xlsx")
folio_output, folio_stats = folio_pipeline.run(folio_opts)
print(f"FOLIO 流程完成，输出至: {folio_output}")

# 2. 运行豆瓣评分流程
douban_pipeline = DoubanRatingPipeline()
douban_opts = DoubanRatingPipelineOptions(excel_file="借阅数据.xlsx")
douban_output, douban_stats = douban_pipeline.run(douban_opts)
print(f"豆瓣流程完成，输出至: {douban_output}")
```

#### 通过 PipelineRunner 串行调用
`PipelineRunner` 用于编排完整的端到端流程，以下是其在 `douban_main.py` 中用法的简化示例。
```python
from src.core.douban.pipelines import (
    PipelineRunner,
    PipelineExecutionOptions,
    FolioIsbnPipelineOptions,
    DoubanRatingPipelineOptions
)

# 定义两条流水线的配置
folio_opts = FolioIsbnPipelineOptions(excel_file="借阅数据.xlsx")
douban_opts = DoubanRatingPipelineOptions(excel_file="借阅数据.xlsx")

# 定义执行器选项
exec_opts = PipelineExecutionOptions(
    excel_file="借阅数据.xlsx",
    folio_options=folio_opts,
    douban_options=douban_opts
)

# 运行
runner = PipelineRunner()
results = runner.run_full_pipeline(exec_opts)
print(results)
```

## 目录结构
```
src/core/douban/
├── analytics/                  # 主题评分统计与动态阈值过滤
├── api/                        # Subject API 客户端与字段映射
├── database/                   # 数据库功能与查重
├── link_resolver/              # Playwright登录与链接采集
├── pipelines/                  # 阶段化流水线实现
│   ├── base.py                   # 流水线基类
│   ├── douban_db_stage.py      # 数据库阶段
│   ├── douban_link_pipeline.py # 链接获取阶段
│   ├── douban_subject_pipeline.py # Subject API 阶段
│   ├── douban_rating_pipeline.py # 豆瓣评分主流水线
│   ├── folio_isbn_pipeline.py    # FOLIO ISBN流水线
│   └── pipeline_runner.py      # 流水线编排器
├── progress_manager.py         # 状态管理与断点续跑
├── report_generator.py         # TXT 报告生成
└── douban_main.py              # CLI入口
```

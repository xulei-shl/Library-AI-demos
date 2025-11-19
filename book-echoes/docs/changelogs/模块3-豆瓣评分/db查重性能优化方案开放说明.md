# 模块3-豆瓣评分 · db查重性能优化方案开放说明

## 背景
- 当前 `isbn` 批量处理流程在导入 Excel 后，会先进行数据库查重再回填已有数据，随后才进入异步爬取阶段。
- 线上运行日志显示：700+ 条“已有有效数据”需要逐条写回 Excel，导致初始阶段耗时巨大；实际爬虫只跑了一个工作器，并在每次调用之间固定等待 4s+。
- 现阶段团队希望先整理优化方向及依赖，后续再逐条落地。

## 核心瓶颈
1. **数据库回填逐条落盘**：`save_interval == 1` 时，`_process_existing_valid_books()` 每合并一条记录都会整表保存一次 Excel，I/O 成为瓶颈。
2. **串行爬取**：配置 `max_concurrent = 1`，再叠加 Folio 固定 `delay = 4s` 和 worker 内部 0.5–2s 的扩展延迟，导致 ISBN 查询吞吐极低。
3. **缺乏批量 DB 访问优化**：虽然已按条码做批量查重，但 SQLite 层缺少显式索引配置说明，也没有缓存/增量校验，重复跑大批量数据依旧很慢。
4. **写入策略粗粒度**：Excel 重写采用临时文件 + 覆盖方式，即便只更新一个单元格也要导出全表，耗时与文件行数线性相关。

## 建议方案
### 1. 数据库读写优化
- 为 `books_history`（或同等表）补充唯一索引：`CREATE UNIQUE INDEX idx_books_barcode ON books(barcode);`。
- 批量查重后一次性返回 `dict[barcode] -> data`，避免在 `_process_existing_valid_books()` 内重复查找。
- 引入“回填缓存表/视图”：记录 Excel 最近写入时间，与 DB 记录的 `updated_at` 对比；一致时直接跳过写回。

### 2. Excel 写入节流
- 将 `save_interval` 默认抬高到 25/50，或改成“累计 N 次/间隔 T 分钟”再落盘；异常退出前在 `finally` 中强制 flush。
- 采用增量写策略：先把更新集合写入 CSV/SQLite，最后再一次性 merge 回原 Excel，或使用 openpyxl 的 streaming write 只改动需要的行。
- 若必须即时同步，可在 `_save_single_result` 里按行复制并保存到一个轻量“快照”文件，主 Excel 只在阶段性检查点落盘。

### 3. 并发与节流策略
- 根据 Folio 接口允许的 QPS，逐步把 `max_concurrent` 提到 2–3，并引入集中式 rate limiter（全局令牌桶），避免每个 worker 自己 sleep。
- 将 `isbn_resolver.delay` 调整为可配置区间（如 1.5–2.5s），并根据实时失败率动态放宽或收紧；必要时为夜间/周末运行提供更激进 preset。
- 预热/复用浏览器实例：复用 Playwright context，减少每轮登录耗时。

### 4. 缓存与增量机制
- 将“已有有效”集合缓存到本地 SQLite/Redis，并标记 Excel 行索引，后续运行直接读取而不用重新匹配 DataFrame。
- 在 `_find_row_index` 预先构建 `barcode -> row_index` map（一次 O(n)），避免对每条记录做线性搜索。
- 为失败/重试记录建立单独表，便于断点续跑，也方便统计真正需要重新爬取的比例。

## 已落实优化（2025-11-xx）
- **数据库层**：database_manager.py 已将 idx_books_barcode 升级为 UNIQUE INDEX，_process_existing_valid_books 也会按条码去重、比对 updated_at 并缓存写回结果，避免重复落盘。
- **Excel 写入节流**：ISBNAsyncProcessor 新增 _stage_result/_maybe_flush_results，按“条数 + 时间”双阈值增量 flush，所有路径（批处理、重试、finally）退出前都会 orce flush，替代 save_interval=1 时的逐条整表写。
- **默认配置更新**：config/setting.yaml 默认并发调至 3、延迟 1.5–2.5s，并提供 save_interval_seconds=180；CLI/Pipeline 的 save_interval 默认值同步到 25，支持 --save-interval 0 仅在结束时保存。
- **行索引缓存**：读取 Excel 时会构建 arcode -> row_index 映射，_find_row_index 命中缓存即可 O(1) 返回，如发现重复条码会输出警告日志。
- **失败分类同步**：以“跳过/获取失败/错误”开头的结果只在最终阶段写回，其余结果进入增量缓冲；重试逻辑与主流程共享缓冲，统计口径一致。

## 开放事项
1. 评估并确认 Folio 接口的并发/速率上限，作为修改 `max_concurrent` 与 `delay` 的前置条件。
2. 设计新的写入策略：选择“批量 flush” vs “增量写”方案，并明确异常情况下的数据一致性保障。
3. 数据库结构若需新增索引/字段，需在 `runtime/database` 下补充迁移脚本，避免手工改库。
4. 若引入缓存/速率自适应，需要补充监控日志格式，便于观察吞吐、失败率和节流行为。

## 验证与回滚
- 优化完成后需记录：单次运行的行数、耗时、平均请求间隔、失败重试次数，与当前基线对比 ≥30% 提升才算达标。
- 每项优化应具备开关（例如通过 `setting.yaml`），方便快速回滚至旧策略。

> 本说明用于指导模块 3（豆瓣评分）的后续编码，后续实现请在提交前更新本文件的“验证”小节，确保信息一致。

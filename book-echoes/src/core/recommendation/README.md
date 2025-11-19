# 智能推荐模块 (Recommendation Module)

## 模块定位与职责

模块 4 负责对候选图书执行“初评 → 终评”的两阶段 LLM 精选，并把评审结果实时写回来源 Excel。核心目标：

- 读取所有 `候选状态 == 候选` 的记录。
- 依据 `索书号` 首字母自动归类主题、控制推荐配额。
- 构造结构化 Prompt 批量调用 LLM，解析 JSON 返回。
- 把“通过/未通过、得分、理由、淘汰原因”等列写回原表，便于人工复核。

## 输入输出要求

- **输入 Excel**：需要包含 `书目条码、书名、豆瓣副标题、豆瓣作者、豆瓣丛书、豆瓣内容简介、豆瓣作者简介、豆瓣目录、索书号、候选状态` 等字段（与模块 2/3 输出保持一致）。
- **输出 Excel**：直接覆盖写回同一文件，自动补齐以下列：
  - 初评：`初评结果 / 初评分数 / 初评理由 / 初评淘汰原因 / 初评淘汰说明`
  - 终评：`终评结果 / 终评分数 / 终评理由 / 终评淘汰原因 / 终评淘汰说明`

## 执行流程

`controller.py` 暴露三个入口函数来串联整个流程：

1. **初评 `run_theme_recommendation_initial(excel_path)`**
   - `group_by_theme`：读取 Excel 后按 `索书号` 首字母归一化（`A-Z/Other`）分主题。
   - `split_batches`：每个主题再按 `MAX_BATCH_SIZE = 20` 等比分批，避免一次调用塞入过多书目。
   - `RecommendationExecutor.initial`：调用 `prompt_builder.build_initial_prompt` 生成 Prompt，再通过 `UnifiedLLMClient` 的 `theme_initial` 任务获取 JSON（失败时自动切换 mock 数据）。
   - `ExcelRecommendationWriter.write_initial`：基于 `书目条码` 定位行、带幂等校验地写入初评结果，并返回所有通过书目的 `selected` 列表以及 `初评理由`。

2. **终评 `run_theme_recommendation_final(excel_path, selected_with_reason)`**
   - 直接复用初评得到的书目列表。
   - `RecommendationExecutor.final`：构造终评 Prompt，触发 `theme_final` 任务（或 mock）。
   - `ExcelRecommendationWriter.write_final`：写入终评结果列。

3. **整合 `run_theme_recommendation_full`**
   - 顺序执行初评 → 终评，额外负责把初评产出的理由透传给终评 Prompt。

## 关键代码组件

| 文件 | 作用 |
| --- | --- |
| `controller.py` | 模块入口，负责任务编排和阶段衔接。 |
| `theme_grouper.py` | 主题归一化与批次切分工具，确保请求粒度稳定。 |
| `prompt_builder.py` | 拼接结构化书目文本，并在初评阶段注入推荐配额提示。 |
| `executor.py` | 封装 LLM 调用、结果解析、mock 降级及错误日志。 |
| `excel_writer.py` | 管理 Excel 读写、条码定位和“只写入空单元格”的幂等控制。 |
| `config.py` | 加载 `config/llm.yaml`（或 `THEME_LLM_CONFIG`）以提供推荐配额、批次大小、主题标准化等配置。 |

## 运行方式

### 1. 独立调用（便于脚本或 Notebook 调试）

> 先在仓库根目录执行 `pip install -r requirements.txt`。

- **只跑初评**：

```bash
python -c "from src.core.recommendation.controller import run_theme_recommendation_initial as run; run('runtime/outputs/月归还数据筛选结果_20240101_120000.xlsx')"
```

- **只跑终评**（需要手动提供初评返回的 `selected` 数据）：

```bash
python - <<'PY'
from src.core.recommendation.controller import run_theme_recommendation_final
excel = "runtime/outputs/月归还数据筛选结果_20240101_120000.xlsx"
# 假设已缓存初评返回的 selected_with_reason
run_theme_recommendation_final(excel, selected_with_reason)
PY
```

- **完整两阶段（推荐）**：

```bash
python -c "from src.core.recommendation.controller import run_theme_recommendation_full as run; run('runtime/outputs/月归还数据筛选结果_20240101_120000.xlsx')"
```

所有命令都会直接对传入的 Excel 进行写回。

### 2. 集成主程序运行（推荐给业务同学）

`main.py` 在菜单中已经挂载模块 4 的两个入口（见 `main.py:372-471`）：

| 菜单编号 | 说明 | 对应函数 |
| --- | --- | --- |
| `4` | 模块 4 —— 仅执行初评流程 | `run_theme_module_initial` → `run_theme_recommendation` |
| `5` | 模块 4 —— 初评 + 终评完整流程 | `run_theme_module_full` → `run_theme_recommendation_full` |

执行步骤：

```bash
python main.py
```

根据提示输入 `4` 或 `5`，程序会自动定位 `runtime/outputs` 目录下最新的模块 3 结果 Excel，然后执行对应流程并输出日志。

## 配置与参数

- **LLM 任务配置**：默认读取 `config/llm.yaml` 中的 `tasks.theme_initial`、`tasks.theme_final`。可通过环境变量 `THEME_LLM_CONFIG=/path/to/custom.yaml` 覆盖。
- **推荐配额**：内置区间规则（`>20:6、15-20:5、10-15:4、5-10:3、<5:2`），也可在 LLM 配置里通过 `tasks.theme_initial.parameters.recommend_quota` 覆写。
- **批次大小**：`MAX_BATCH_SIZE = 20`，需要调整可修改 `config.py` 或调用 `split_batches` 时传入自定义值。
- **日志**：全模块共享 `src.utils.logger`，运行时会输出主题分组、调用状态及写回结果，便于排查。

## 调试与降级策略

- 当 `UnifiedLLMClient` 初始化或远程调用失败时，`RecommendationExecutor` 会自动使用 mock 逻辑（基于书名长度的简易评分），仍可完成整条流程，方便在离线环境验证 Excel 写入与流程编排。
- `ExcelRecommendationWriter` 在写入前会检查目标单元格是否已有有效值（为空或 `ERROR:` 开头才会重写），避免重复运行时覆盖人工修改。
- `_safe_parse_json` 会自动从 Markdown fenced code 中提取 JSON，并在解析失败时返回空结构，保证 Excel 写回逻辑稳健。

以上信息覆盖了模块的功能、运行逻辑以及集成方式，便于在独立调试与主程序中快速使用。***

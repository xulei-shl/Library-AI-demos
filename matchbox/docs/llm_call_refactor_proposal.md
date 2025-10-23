# 大模型调用流程重构建议

本文档根据现有代码逻辑与业务目标，提出针对大模型（LLM/VLM）调用流程的优化与重构方案，以简化调用链、减少不必要的重复调用，并提升共识生成阶段的性能与一致性。

---

## 一、现状问题

### 1. 系列场景（Series Processing）
- **阶段1**：当前对 A 类型的 series 样本组仅调用一次 [`series.execute_stage()`](../src/core/stages/series.py)，生成包含 `name` 等字段的 JSON，并未拆分为事实字段与艺术风格的独立调用。
- **阶段2**：共识生成阶段（`series_consensus`）并未复用阶段1的 JSON，而是重新对参与共识的每个样本组调用 [`art_style.execute_stage()`](../src/core/stages/art_style.py) 与 [`fact_description.execute_stage()`](../src/core/stages/fact_description.py)，统一 noseries=False。这导致性能开销大且与阶段1的输出存在冗余。

### 2. 非系列场景（Non-Series Processing）
- 当前流程符合预期：每个组依次经过 `fact_description` → `art_style` → `function_type` → `correction` 四阶段生成最终 JSON，无多余调用。

---

## 二、重构目标

1. **避免重复调用**  
   阶段2应直接利用阶段1已经生成的 JSON，减少重复的 LLM/VLM 调用。
2. **拆分系列样本的处理**  
   对 A 类型的 series 图像在阶段1拆分为两次调用：
   - 事实字段（fact_description，不含艺术风格）
   - 艺术风格（art_style，仅按候选词表）
3. **确保共识字段更新**  
   共识生成结果必须直接更新回阶段1的 JSON 文件（系列 JSON 与对象 JSON）。

---

## 三、重构方案

### 1. 阶段1：初步处理
#### （1）A 类型 series 样本组
- **第一次调用**：`fact_description`  
  - noseries=False  
  - 提示模板修改为“仅生成事实字段（series.name、manufacturer、country等），不包含艺术风格”
- **第二次调用**：`art_style`  
  - 使用候选词表，确保与对象组的艺术风格标签一致
- **合并结果**：将两次调用结果合并生成完整的 `series.json`

#### （2）A 类型对象组 & B 类型对象组
- 顺序保持不变：`fact_description` → `art_style` → `function_type`
- noseries 对 A 类型对象组可保持现状（根据业务需求选择是否调整为 noseries=False）

---

### 2. 阶段2：系列共识生成（简化版）
- **样本来源**：直接读取阶段1生成的 `series.json` 与对象组 JSON
- **字段选择**：提取 `series_name`、`manufacturer`、`country`、`art_style`
- **单次调用**：将样本传入文本模型 `series_consensus` 进行投票与共识生成
- **结果更新**：将共识结果字段回填到阶段1的系列 JSON 与对象 JSON

---

### 3. 场景二：非系列处理流程
- 保持现状：  
  `fact_description` → `art_style` → `function_type` → `correction`  
  每个组 4 次调用

---

## 四、预期调用次数变化（示例：1 个 A 类型系列样本 + 3 个对象组）

- **现状**：  
  阶段1：1 + (3×3) = 10 次  
  阶段2：3 + 3 + 1 = 7 次  
  总计 = **17 次调用**

- **重构后**：  
  阶段1：2（series: fact + art） + 9（对象组） = 11 次  
  阶段2：1（series_consensus） = 1 次  
  总计 = **12 次调用**（减少 5 次调用）

---

## 五、代码调整位置

1. **`src/core/orchestration/series_processor.py`**  
   - 替换当前对 `series.execute_stage()` 的调用为：
     ```python
     fact_json, fact_meta = fact_description.execute_stage(g.image_paths, settings)
     art_json, art_meta = art_style.execute_stage(g.image_paths, settings)
     series_json = {**fact_json, **art_json}
     ```
   - 确保合并逻辑和 meta 信息写入 JSON 文件

2. **`src/core/consensus/manager.py`**  
   - 修改 `_build_metadata_samples_for_consensus()` 取消二次调用 `fact_description` 与 `art_style`
   - 改为从阶段1生成的 JSON 文件读取字段

3. **`src/core/updates/json_consensus_update.py`**  
   - 添加用于将共识结果字段回填到 series.json 和对象 JSON 的函数

4. **提示模板文件（`src/prompts/fact_description.md` / `src/prompts/art_style.md`）**  
   - 增加针对 series 阶段的专用提示，明确“fact阶段不生成艺术风格”、“art阶段使用候选词表”

---

## 六、重构流程图

```mermaid
flowchart TD
    A0[输入图像分组] --> A1a[阶段1: A 类型 series fact_description(noseries=False,不含风格)]
    A1a --> A1b[art_style(候选词表)]
    A1b --> A1c[合并为完整 series.json]

    A0 --> A2[阶段1: A/B 对象组 fact_description → art_style → function_type]
    A2 --> A3[写出对象 json]

    A1c --> B1[阶段2: 读取阶段1 JSON 生成样本]
    A3 --> B1
    B1 --> B2[单次 series_consensus(text-only)]
    B2 --> B3[更新系列及对象 JSON 字段]
```

---

## 七、结论
此重构方案可显著减少 LLM/VLM 调用次数，提升性能，同时保持或提升共识生成的字段一致性。
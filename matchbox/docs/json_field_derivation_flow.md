# JSON 字段取值全流程梳理

本文档旨在梳理系统针对A、B、C三种不同图像组织方式，最终JSON字段的取值全流程。

### **总体流程概述**

整个处理流程可以概括为三个核心步骤：

1.  **图像分组 (`image_grouping.py`)**: 系统首先扫描输入目录，根据文件结构和命名规则，将所有图片识别并划分为不同的“图像组”(ImageGroup)。每个组被标记为特定类型（`a_series`, `a_object`, `b`），这直接对应文档中的A、B、C三种组织方式。
2.  **系列共识 (`pipeline.py`)**:
    *   仅对存在“系列边界”的目录参与（A 类型的对象目录与 B 类型的系列目录）。为每个系列生成一个共识文件 (`.series_consensus.json`)。
    *   共识文件决定该系列所有对象最终的 **系列级字段**：`series_name`, `manufacturer`, `country`, `art_style`。
    *   若共识文件不存在，系统抽取若干对象样本执行初步分析，再通过 `series_consensus` 任务（LLM 投票）生成并保存共识。
    *   C 类型（根目录扁平）不创建共识文件，不进行系列级字段统一。
3.  **对象处理与字段合并 (`pipeline.py`)**: 系统遍历每一个图像组，按顺序执行多个分析阶段（事实描述、艺术风格、功能类型等），生成初步的元数据。然后，将“系列共识”中的字段值强制覆盖到初步元数据上。最后，再进行一次校验和纠正，最终生成每个图像组的 JSON 文件。

---

### **A 类型：带系列文件夹的子目录 (`pic/S1/series/` 和 `pic/S1/object-group/`)**

这种类型包含两种图像组：`a_series`（系列样本）和 `a_object`（普通对象组）。

1.  **系列样本处理 (`a_series`)**:
    *   **触发**: 首先处理 `pic/S1/series/` 目录下的图像组。
    *   **执行阶段**: 调用 `series.execute_stage`，这个阶段专门用于从系列样本图像中提取高级系列信息。
    *   **字段来源**:
        *   `name` (系列名称), `manufacturer`, `country`, `theme`, `description`, `art_style` 等字段由 `series` 阶段的LLM（提示词: `series.md`）分析得出。
        *   最终会为这个系列样本本身生成一个独立的JSON文件（例如 `S_A001.json`），并将其结果（尤其是 `series.name`）暂存起来，作为后续处理该系列下其他对象时的上下文（`series_ctx`）。

2.  **系列共识生成**:
    *   **触发**: 在处理普通对象组之前，检查 `pic/S1/.series_consensus.json` 文件是否存在。
    *   **生成逻辑**: 如果文件不存在，系统会：
        *   从 `a_object` 组中选取N个样本（默认为3个）。
        *   对每个样本执行 `fact_description` 和 `art_style` 阶段。
        *   **关键点**: 在调用 `series_consensus.execute_stage` 进行投票时，会把上一步从 `a_series` 样本中得到的 `series.name` 作为 **固定值** (`fixed_series_name`) 传入，指示LLM不再对系列名称进行投票，直接使用该值。
        *   LLM（提示词: `series_consensus.md`）会对 `manufacturer`, `country`, `art_style` 进行投票，并结合固定的 `series_name` 生成共识。
        *   共识结果写入 `.series_consensus.json`。

3.  **普通对象处理 (`a_object`)**:
    *   **触发**: 处理 `pic/S1/` 目录下（非 `series` 子目录）的普通图像组。
    *   **执行阶段与字段来源**:
        1.  **`fact_description`**: 执行事实描述（`noseries=True` 模式，不提取系列信息），生成 `description`, `elements`, `text_content`, `theme` 等基础字段。
        2.  **`art_style`**: 添加 `art_style` 和 `art_style_raw` 字段。
        3.  **`function_type`**: 添加 `function_type` 字段。
        4.  **`merge_series_name_into_object`**: 将步骤1中暂存的 `series.name` 合并进来。
        5.  **`merge_series_consensus_into_object` (关键覆盖步骤)**: 读取 `.series_consensus.json` 文件，用其中的 `series_name`, `manufacturer`, `country`, `art_style` **强制覆盖** 当前对象已有的同名字段。**这是确保系列内所有对象系列级字段统一的核心步骤。**
        6.  **`correction`**: 基于 `text_content` 对 `manufacturer`, `country`, `series.name` 等字段进行最终的校验和修正。
        7.  **输出**: 生成最终的JSON文件。

---

### **B 类型：同一系列的图像文件 (`pic/S1/id-1.jpg`, `pic/S1/id-2.jpg`)**

这种类型在代码中被识别为 `a_object` 组，但它们所在的目录没有 `series` 子目录。

1.  **系列共识生成**:
    *   **触发**: 系统发现 `pic/S1/` 目录下有多组图像，它们共享同一个共识文件路径 `pic/S1/.series_consensus.json`。
    *   **生成逻辑**: 由于没有 `a_series` 样本，`series_ctx` 为空。
        *   系统直接从这些 `a_object` 组中选取N个样本。
        *   对每个样本执行 `fact_description` (`noseries=True` 模式) 和 `art_style`。
        *   调用 `series_consensus.execute_stage` 进行投票。此时 **所有系列级字段** (`series_name`, `manufacturer`, `country`, `art_style`) 都由LLM基于N个样本的初步分析结果投票决定。
        *   共识结果写入 `.series_consensus.json`。

2.  **对象处理**:
    *   **执行阶段与字段来源**:
        1.  **`fact_description`**: 执行事实描述（`noseries=True` 模式）。
        2.  **`art_style`**: 添加 `art_style` 和 `art_style_raw`。
        3.  **`function_type`**: 添加 `function_type`。
        4.  **`merge_series_consensus_into_object` (关键覆盖步骤)**: 读取 `.series_consensus.json`，用共识值强制覆盖 `series.name`, `manufacturer`, `country`, `art_style`。
        5.  **`correction`**: 进行最终校验和修正。
        6.  **输出**: 生成最终的JSON文件。

---

### **C 类型：基于 ID 的扁平结构 (`id-1.jpg`, `id-2.jpg`)**

这种类型在代码中被识别为 `b` 类型图像组，位于根输入目录下。

1.  **不生成系列共识**:
    *   根目录扁平（C 类型）各对象组独立处理，不创建 `.series_consensus.json` 文件；不进行系列级字段统一。

1.  **对象处理**:
    *   **执行阶段与字段来源**:
        1.  **`fact_description`**: 执行事实描述（`noseries=False` 模式），按对象自身提取基础字段（如有 `series` 信息，仅作为对象自有字段，不做统一）。
        2.  **`art_style`**: 添加 `art_style` 和 `art_style_raw`。
        3.  **`function_type`**: 添加 `function_type`。
        4.  **`correction`**: 进行最终校验和修正。
        5.  **输出**: 生成最终的JSON文件。

### **总结与对比**

| 特征 / 类型 | A 类型 (带series文件夹) | B 类型 (系列文件夹内平铺) | C 类型 (根目录平铺) |
| :--- | :--- | :--- | :--- |
| **系列名称来源** | **`a_series` 样本** (`series`阶段) 提供权威名称，共识阶段直接采用。 | **LLM投票** (`series_consensus`阶段) 从多个对象样本中选举产生。 | 不适用（不做系列统一）/ 按对象自有推断。 |
| **其他系列字段来源** | **LLM投票** (`series_consensus`阶段) 选举产生，但 `series.name` 是固定的。 | **LLM投票** (`series_consensus`阶段) 选举产生。 | 不适用（不做系列统一）/ 按对象自有推断。 |
| **`fact_description`模式** | 对象组使用 `noseries=True` | 对象组使用 `noseries=True` | 对象组使用 **`noseries=False`** |
| **最终字段确定** | 基础字段 -> 共识字段覆盖 -> 修正 | 基础字段 -> 共识字段覆盖 -> 修正 | 基础字段 -> 修正 |

总而言之，系统对 A/B 类型采用 **“共识优先”** 的设计：识别系列边界并为该系列建立统一、权威的系列级元数据；而 C 类型按对象独立处理，不进行系列级字段统一。对于 A/B 类型对象，其自身分析结果提供基础信息，但最终的系列相关字段（`series.name`, `manufacturer`, `country`, `art_style`）由系列共识文件强制统一；对于 C 类型，仅进行对象级生成与校验。

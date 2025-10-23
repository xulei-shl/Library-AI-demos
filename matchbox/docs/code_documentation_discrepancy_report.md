# 代码与文档一致性分析报告

本文档旨在记录 `src/core/pipeline.py` 中的核心处理逻辑与 `docs/图像运行过程梳理.md` 文档描述之间的不一致性。

通过详细分析，发现代码的实际执行逻辑与文档在 **`correction` (修正) 阶段的处理**上存在显著差异。这些差异可能导致非预期的处理行为，并与设计初衷相悖。

---

## 核心差异点

### 1. A/B 类型 `correction` 阶段的执行逻辑不一致

-   **文档描述**:
    对于 A 类型和 B 类型（即包含系列共识的类型），文档明确指出：“在应用共识字段后**跳过 `correction` 阶段**，避免不必要的再次校验。” 这意味着 A/B 类型在生成最终 JSON 时不应执行 `correction` 阶段。

-   **代码实现 (`src/core/pipeline.py`)**:
    代码的当前逻辑是，在为 A/B 类型的对象组（`object_groups`）生成初始 JSON 文件时，就已经执行了 `correction` 阶段。这发生在系列共识数据被应用**之前**，与文档描述的“跳过”策略完全相反。

    ```python
    # src/core/pipeline.py L348-L355 (大致位置)
    # 在处理对象组（A/B类型）的循环中
    
    # ... fact_description, art_style, function_type 等阶段 ...

    # Stage 3: Structured field correction (text-based validation)
    # 此处在应用共识前就执行了 correction
    corr_json, corr_meta = correction.execute_stage(
        g.image_paths, settings, context={"input_json": fact_json}
    )
    # ...
    ```

### 2. 应用共识后存在无效的 `correction` 逻辑

-   **文档描述**:
    文档强调只有 C 类型（无系列关联的独立对象）会执行 `correction` 阶段。

-   **代码实现 (`src/core/pipeline.py`)**:
    在代码的末尾，当批量循环所有 JSON 文件以应用共识数据（`consensus_data`）时，存在一段尝试为 `group_type == "c"` 的组再次执行 `correction` 的逻辑。

    ```python
    # src/core/pipeline.py L401-L414 (大致位置)
    # 在批量更新JSON文件的循环中
    
    # ... 合并共识字段 ...
    
    # 仅在 C 类型需要 correction，其它类型跳过 correction
    # ...
    if group_type == "c":
        corr_json, corr_meta = correction.execute_stage(
            [], settings, context={"input_json": obj_json}
        )
        # ...
    ```

    这段代码存在两个严重问题：
    1.  **无效的类型判断**: 根据图像分组模块 `src/core/image_grouping.py` 的实现，`discover_image_groups` 函数只会生成 `'a_series'`, `'a_object'`, `'b'` 这三种 `group_type`。代码中**不存在 `group_type == "c"` 的情况**，因此 `if group_type == "c"` 这个条件永远不会被满足，导致该代码块是无法触及的“死代码”。
    2.  **逻辑位置错误**: C 类型的图像组（即根目录下的图片）在代码中是作为 `_no_series_` 分支处理的，它们根本不会进入应用系列共识的循环体中。这进一步证明了此处的 `correction` 调用逻辑是错误的，并且与整体架构不符。

---

## 结论

代码与文档的核心矛盾在于 **`correction` 阶段的执行时机和条件**。

-   **文档**清晰地定义了 C 类型执行修正，而 A/B 类型为了效率和数据一致性应跳过修正。
-   **代码**的实现不仅在处理 A/B 类型时错误地执行了修正，还在一个不相关的流程中包含了一段针对 C 类型的、永远不会被执行的无效修正逻辑。

建议根据 `docs/图像运行过程梳理.md` 中的设计规范来修正 `src/core/pipeline.py` 的处理流程，以确保代码行为与设计文档保持一致。

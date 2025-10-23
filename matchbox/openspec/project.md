# 项目上下文

## 项目目的
Matchbox 是一个基于视觉的 AI 系统，用于分析和编目图书馆资料（特指"火花"或火柴盒标签），使用大型视觉语言模型。系统对图像进行多阶段分析，生成结构化元数据，包括事实描述、功能类型分类和系列信息。

## 技术栈
- **语言**: Python 3.x
- **核心依赖**:
  - OpenAI SDK (用于 LLM API 调用)
  - python-dotenv (环境变量管理)
  - PyYAML (配置管理)
- **API**: 支持多个 LLM 提供商 (ModelScope, Qwen, SophNet, DeepSeek)
- **数据格式**: YAML (配置), JSON (结构化输出), Excel (最终导出)

## 项目约定

### 代码风格
- UTF-8 编码，显式声明 (`# -*- coding: utf-8 -*-`)
- 领域特定内容可使用中文注释和文档
- 函数/变量命名: snake_case
- 模块结构: `src/` 源代码, `config/` 配置, `runtime/` 输出
- 日志: 结构化日志，敏感数据预览截断

### 架构模式
项目采用**两阶段模块化管道架构**，将图像处理根据是否属于系列（Series）进行分离，以实现高效的共识生成和数据一致性。

- **核心编排层 (`src/core/pipeline.py`)**: 作为轻量级编排器，负责发现和分组图像，然后将不同类型的图像组委托给专门的处理器。

- **专用处理器**:
  - **系列处理器 (`src/core/orchestration/series_processor.py`)**: 处理 A 和 B 类型的图像组。此处理器仅执行流程的**第一阶段**，即为系列中的所有对象和样本生成初始的元数据 JSON 文件。
  - **非系列处理器 (`src/core/orchestration/no_series_processor.py`)**: 处理 C 类型的图像组。它执行一个简化的线性流水线，一次性完成所有处理阶段。

- **共识管理 (`src/core/consensus/manager.py`)**: 在系列处理器的第一阶段完成后，此模块负责为每个系列生成或读取共识数据。它触发 `series_consensus` 阶段，对样本元数据进行投票，并将结果持久化到源图像目录下的 `.series_consensus.json` 文件中。

- **更新与终结 (`src/core/updates/json_consensus_update.py`)**: 此模块执行流程的**第二阶段**。它读取共识文件，将共识字段（如 `manufacturer`, `country`, `art_style`）批量更新到该系列所有相关的 JSON 文件中，并根据图像类型决定是否执行最终的修正。

#### 处理流程详解

- **A/B 类型 (系列) 处理流程**:
  1.  **阶段一：初始 JSON 生成**:
      - `series_processor` 对系列中的每个对象（或样本）依次执行 `fact_description` -> `art_style` -> `function_type` 等初始阶段。
      - 为每个对象在 `runtime/outputs/` 目录下生成一个独立的、临时的 JSON 文件。
  2.  **阶段二：共识、应用与修正**:
      - `consensus_manager` 确保为该系列生成 `.series_consensus.json` 文件。
      - `json_consensus_update` 读取共识数据，并将其**批量覆盖**到第一阶段生成的所有 JSON 文件中。
      - **重要**: 由于系列级别字段已通过共识保证一致，A 和 B 类型在应用共识后**跳过 `correction` 阶段**，以避免不必要的重复校验。

- **C 类型 (非系列) 处理流程**:
  1.  **线性流水线**:
      - `no_series_processor` 对每个对象执行一个完整的、线性的处理流程：`fact_description` -> `art_style` -> `function_type` -> `correction`。
      - 所有处理在一个步骤内完成，直接生成最终的 JSON 文件。
      - 此流程不涉及任何系列共识。

### 测试策略
- 开发过程中的手动测试
- 通过 JSON schema 修复和验证工具进行验证
- 覆盖保护: `overwrite_existing` 标志防止意外重复处理

### Git 工作流
- **主分支**: `main`
- **提交风格**: 可使用中文提交信息，简洁描述
- **工作流**: 小改动直接提交到 main，大型工作使用特性分支

## 业务领域上下文
- **领域**: 图书馆资料编目和归档
- **主要文物**: 火花 (huohua) - 历史火柴盒标签/图像
- **分析类型**:
  - **事实描述**: 物理特征、视觉元素、文本内容
  - **艺术风格**: 视觉表现手法分类（基于 13 个标准化类别词表）
  - **功能类型**: 按用途/主题分类（基于受控词表）
  - **系列分析**: 将相关项目分组为集合
- **图像组织方式**:
  - **A 类型**: 位于子目录中，且包含 `series` 子目录。
  - **B 类型**: 位于子目录中，但不包含 `series` 子目录，同一子目录下的图片视为一个系列。
  - **C 类型**: 直接位于根目录下，按文件名前缀分组，被视为独立的、无系列关联的对象。
- **命名约定**: 图像文件使用前缀分组（例如 `A001-1`, `A001-2` 属于组 `A001`）

## 重要约束
- **禁止虚构**: LLM 输出不得编造信息；缺乏证据时必须使用空值。
- **基于证据的年代判定**: 历史年代判定必须使用最高级别的可用证据。
- **系列级字段一致性**: 同一系列的所有对象必须共享相同的系列级字段（`series.name`, `manufacturer`, `country`, `art_style`）。这通过两阶段处理流程中的**共识生成与批量应用**机制来强制保证。
- **API 速率限制**: 可配置速率限制 (`rate_limit_ms`) 和重试策略。
- **超时要求**: 视觉任务通常需要 60-180 秒超时。
- **输出验证**: 所有 JSON 输出在接受前必须通过修复/验证。
- **系列提取**: 写入 Excel 时，系列信息仅展平为 `name` 字段。

## 系列共识文件
每个系列文件夹下会生成 `.series_consensus.json` 文件，用于持久化系列级元数据的共识结果：

- **位置**:
  - A 类型: `pic/S1/.series_consensus.json`
  - B 类型: `pic/S1/.series_consensus.json`
- **格式**:
  ```json
  {
    "series_name": "中国名胜",
    "manufacturer": "北京火柴厂",
    "country": "中国",
    "art_style": "写实风景画",
    "consensus_source": ["A001", "A002", "A003"],
    "consensus_meta": {
      "created_at": "2025-10-19T14:30:00+08:00",
      "llm_model": "DeepSeek-V3.2-Exp",
      "consensus_strategy": "llm_vote",
      "sample_size": 3
    }
  }
  ```
- **作用**: 保证同一系列的所有对象使用一致的系列级字段，支持增量处理和断点续传。
- **配置**: 可通过 `settings.yaml` 中的 `series_consensus.sample_size` 调整样本数量，通过 `series_consensus.force_recalculate` 强制重新计算共识。

## 外部依赖
- **LLM API 提供商**:
  - 主视觉模型: ModelScope (Qwen/Qwen3-VL-235B-A22B-Instruct)
  - 辅视觉模型: Qwen (qwen3-vl-plus)
  - 主文本模型: SophNet (DeepSeek-V3.2-Exp)
  - 辅文本模型: ModelScope (DeepSeek-V3.2-Exp)
- **API 密钥管理**: 通过 `.env` 文件配置环境变量
- **配置文件**: `config/settings.yaml`
- **提示词模板**: `src/prompts/` 中的 Markdown 文件
- **输出目录**:
  - `runtime/outputs/` 存放 JSON 结果
  - `runtime/logs/` 存放执行日志
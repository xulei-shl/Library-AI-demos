# 规范: 艺术风格检测

## ADDED Requirements

### Requirement: 标准化艺术风格词表

系统 SHALL 提供一个标准化的艺术风格分类词表,定义火花常见的艺术表现手法和视觉风格类别。

#### Scenario: 词表包含预定义类别

- **WHEN** 艺术风格检测模块需要识别火花的视觉风格
- **THEN** 系统提供以下 13 个标准分类供 VLM 选择:
  - 写实绘画 (Realistic Painting)
  - 木刻版画 (Woodcut Print)
  - 工笔画 (Gongbi / Meticulous Brush Painting)
  - 水墨画 (Ink Wash Painting)
  - 装饰艺术 (Art Deco)
  - 卡通插画 (Cartoon Illustration)
  - 摄影 (Photography)
  - 剪纸艺术 (Paper-Cutting Art)
  - 年画风格 (Nianhua / New Year Print)
  - 抽象图案 (Abstract Pattern)
  - 素描/线描 (Sketch / Line Drawing)
  - 海报艺术 (Poster Art)
  - 其他 (Other)

#### Scenario: 词表提供详细识别指导

- **WHEN** VLM 需要判断某个艺术风格类别
- **THEN** 词表为每个类别提供:
  - 核心特征描述(线条、色彩、笔触、构图)
  - VLM 识别要点(可观察的视觉线索)
  - 典型示例(常见题材和表现形式)

#### Scenario: 词表文档存储位置

- **WHEN** 用户或开发者需要查阅艺术风格词表
- **THEN** 词表文档存储在 `docs/metadata/艺术风格词表.md`

---

### Requirement: 独立的艺术风格检测模块

系统 SHALL 提供一个独立的处理阶段模块,专门负责艺术风格的识别和提取。

#### Scenario: 模块实现为独立的 Python 模块

- **WHEN** 系统需要执行艺术风格检测任务
- **THEN** 调用 `src/core/stages/art_style.py` 模块的 `execute_stage` 函数

#### Scenario: 模块接受图像路径作为输入

- **WHEN** 艺术风格检测模块被调用
- **THEN** 模块接受以下参数:
  - `image_paths`: `List[str]` - 待分析的图像文件路径列表
  - `settings`: `Dict[str, Any]` - 管道配置字典
  - `context`: `Optional[Dict[str, Any]]` - 可选上下文信息(当前未使用)

#### Scenario: 模块返回检测结果和元数据

- **WHEN** 艺术风格检测完成
- **THEN** 模块返回元组 `(result_json, metadata)`,其中:
  - `result_json`: `Dict[str, Any] | None` - 包含 `art_style` 和 `art_style_raw` 字段的 JSON 对象
    - `art_style`: `List[String] | null` - 1-2 个标准化风格分类(从词表中选择)
    - `art_style_raw`: `List[String] | null` - 1-2 个自由描述的风格词(可选,当规范词表无法精确覆盖时使用)
  - `metadata`: `Dict[str, Any]` - 执行元数据(状态、时间戳、模型、错误信息)

#### Scenario: 模块失败时返回 None

- **WHEN** VLM 调用失败或输出无效
- **THEN** `result_json` 为 `None`,且 `metadata` 包含错误信息

---

### Requirement: 艺术风格检测提示词模板

系统 SHALL 提供专用的提示词模板,指导 VLM 执行艺术风格识别任务。

#### Scenario: 提示词包含完整词表

- **WHEN** 构建艺术风格检测的 VLM 提示词
- **THEN** 提示词包含:
  - 完整的 13 个艺术风格类别定义
  - 每个类别的识别要点和典型示例
  - VLM 提取指导原则(多风格支持、证据优先、排他性规则、双字段输出规则)

#### Scenario: 提示词存储位置

- **WHEN** 系统需要加载艺术风格检测提示词
- **THEN** 从 `src/prompts/art_style.md` 读取模板内容

#### Scenario: 提示词要求 JSON 格式输出

- **WHEN** VLM 执行艺术风格识别
- **THEN** 提示词明确要求输出格式为:
  ```json
  {
    "art_style": ["String", "..."] | null,
    "art_style_raw": ["String", "..."] | null
  }
  ```
- **AND** 提示词说明:
  - `art_style`: 从 13 个标准分类中选择 1-2 个,按主导程度排序
  - `art_style_raw`: 可选,当规范词表无法精确覆盖时,提供自由描述的风格词(1-2 个)

---

### Requirement: 任务配置

系统 SHALL 在配置文件中定义艺术风格检测任务的参数。

#### Scenario: 配置文件包含 art_style 任务

- **WHEN** 系统加载 `config/settings.yaml`
- **THEN** 配置文件包含 `tasks.art_style` 节点,定义:
  - `provider_type`: `vision` (使用视觉模型)
  - `endpoint`: `/chat/completions`
  - `temperature`: `0.2` (低温度提高确定性)
  - `top_p`: `0.9`
  - `system_prompt_file`: `src/prompts/art_style.md`

#### Scenario: 任务使用视觉 API 提供商

- **WHEN** 艺术风格检测模块调用 VLM
- **THEN** 使用 `api_providers.vision` 配置的主辅模型(与事实描述相同)

---

### Requirement: 输出数据验证

系统 SHALL 验证艺术风格检测的输出格式和内容。

#### Scenario: 验证 JSON 格式

- **WHEN** VLM 返回艺术风格检测结果
- **THEN** 系统使用 `fix_or_parse_json` 工具验证并修复 JSON 格式

#### Scenario: 接受合法的规范风格名称列表

- **WHEN** VLM 输出的 `art_style` 为列表,且每个元素为词表中定义的 13 个类别之一
- **THEN** 系统接受该值
- **AND** 列表长度应为 1-2 个元素

#### Scenario: 接受自由描述的风格词

- **WHEN** VLM 输出的 `art_style_raw` 为字符串列表
- **THEN** 系统接受该值(不验证具体内容)
- **AND** 列表长度应为 1-2 个元素

#### Scenario: 接受 null 值

- **WHEN** VLM 输出的 `art_style` 或 `art_style_raw` 值为 `null`(表示无法判断或无需补充)
- **THEN** 系统接受该值

#### Scenario: 处理无效输出

- **WHEN** VLM 输出的 `art_style` 包含不在词表中的值,或列表长度 > 2
- **THEN** 系统记录警告,但仍保留原始值(不强制拒绝,允许后续人工审核)

---

### Requirement: 双字段输出逻辑

系统 SHALL 支持规范词和自由词的双字段输出,允许在标准化分类的同时保留更精确的风格描述。

#### Scenario: 优先使用规范词表

- **WHEN** 火花的艺术风格可归入标准词表的 1-2 个类别
- **THEN** VLM 填充 `art_style` 字段,`art_style_raw` 可为 `null`

#### Scenario: 规范词无法精确覆盖时使用自由词

- **WHEN** 火花的艺术风格无法精确归入任何标准分类
- **THEN** VLM 应:
  - 设置 `art_style` 为 `["其他"]`
  - 在 `art_style_raw` 中提供具体描述(例如 `["赛璐璐动画风格"]`)

#### Scenario: 同时使用两个字段

- **WHEN** 火花的艺术风格可归入标准分类,但需要更精确的描述
- **THEN** VLM 可同时填充:
  - `art_style`: 标准分类(例如 `["装饰艺术"]`)
  - `art_style_raw`: 补充说明(例如 `["Art Nouveau 新艺术运动风格"]`)

#### Scenario: 词表更新策略

- **WHEN** 定期(每季度)回顾 `art_style_raw` 数据
- **THEN** 系统维护人员应:
  - 统计高频自由词(出现频率 > 5%)
  - 评估是否将其纳入标准词表
  - 更新词表后,重新处理历史数据中标记为"其他"的记录

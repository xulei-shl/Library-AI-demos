# 实施任务清单

## 1. 准备工作:创建词表和提示词

- [x] 1.1 创建艺术风格词表文档 `docs/metadata/艺术风格词表.md`(已包含 13 个标准分类和识别指导)
  - 支持双字段输出:`art_style`(规范词) + `art_style_raw`(自由词)
  - 定义多风格支持(1-2 个主导风格)
  - 明确三种使用策略(优先规范词、无法覆盖时使用自由词、同时使用)
- [x] 1.2 创建艺术风格检测提示词模板 `src/prompts/art_style.md`,内容包括:
  - 系统角色定义(火花艺术风格识别专家)
  - 完整的艺术风格词表(13 个类别)
  - VLM 提取指导原则(多风格支持、证据优先、排他性规则、双字段输出规则、空值处理)
  - 输出格式规范(JSON schema):
    ```json
    {
      "art_style": ["String", "..."] | null,
      "art_style_raw": ["String", "..."] | null
    }
    ```
  - 明确说明:
    - `art_style`: 从 13 个标准分类中选择 1-2 个,按主导程度排序
    - `art_style_raw`: 可选,当规范词表无法精确覆盖时,提供自由描述的风格词(1-2 个)

---

## 2. 核心模块开发:艺术风格检测阶段

- [x] 2.1 创建 `src/core/stages/art_style.py` 模块,实现 `execute_stage` 函数:
  - 接受参数:`image_paths`, `settings`, `context`(可选)
  - 调用 `build_messages_for_task("art_style", settings, user_text=None, image_paths=image_paths, as_data_url=True)`
  - 调用 `invoke_model` 使用视觉模型进行艺术风格识别
  - 使用 `fix_or_parse_json` 验证和修复 JSON 输出
  - 返回 `(result_json, metadata)` 元组
- [x] 2.2 在 `src/core/stages/__init__.py` 中导出 `art_style` 模块

---

## 3. 配置集成:添加任务配置

- [x] 3.1 在 `config/settings.yaml` 中的 `tasks` 节点添加 `art_style` 任务配置:
  ```yaml
  art_style:
    provider_type: vision
    endpoint: /chat/completions
    temperature: 0.2
    top_p: 0.9
    system_prompt_file: src/prompts/art_style.md
  ```

---

## 4. 管道编排:集成新阶段

- [x] 4.1 在 `src/core/pipeline.py` 的导入语句中添加 `art_style`:
  ```python
  from src.core.stages import fact_description, function_type, series, correction, art_style
  ```
- [x] 4.2 在 `run_pipeline()` 函数中,对于 `a_object` 和 `b` 类型的图像组,在事实描述后、功能类型前调用艺术风格检测:
  ```python
  # 在 fact_description.execute_stage 之后
  art_result, art_meta = art_style.execute_stage(g.image_paths, settings)
  fact_json["art_style_meta"] = art_meta
  if isinstance(art_result, dict):
      # 合并 art_style 和 art_style_raw 两个字段
      if "art_style" in art_result:
          fact_json["art_style"] = art_result.get("art_style")
      if "art_style_raw" in art_result:
          fact_json["art_style_raw"] = art_result.get("art_style_raw")
  ```
- [x] 4.3 添加错误处理:如果艺术风格检测失败,记录元数据但不中断管道

---

## 5. 清理旧逻辑:移除事实描述中的艺术风格提取

- [x] 5.1 编辑 `src/prompts/fact_description.md`,移除以下内容:
  - 第 126-129 行:艺术风格词条定义
  - 输出 schema 中的 `"art_style": "String | null"` 字段(第 202 行)
- [x] 5.2 编辑 `src/prompts/fact_description-noseries.md`,移除以下内容:
  - 第 111-114 行:艺术风格词条定义
  - 输出 schema 中的 `"art_style": "String | null"` 字段(第 183 行)
- [x] 5.3 确认修改后,事实描述提示词仍包含其他 11 个元数据字段

---

## 6. 测试验证

- [ ] 6.1 运行管道处理测试图像集(至少包含 3 种不同艺术风格的火花)
- [ ] 6.2 验证输出 JSON 包含以下字段:
  - `art_style`: 值为词表中的标准分类列表(1-2 个)或 `null`
  - `art_style_raw`: 值为自由描述的风格词列表(1-2 个)或 `null`
  - `art_style_meta`: 包含 `status`, `executed_at`, `task_type`, `llm_model`, `error`
- [ ] 6.3 验证双字段输出的正确性:
  - 测试规范词表可覆盖的火花:`art_style` 有值,`art_style_raw` 为 `null`
  - 测试无法归类的火花:`art_style` 为 `["其他"]`,`art_style_raw` 有具体描述
  - 测试混合风格的火花:`art_style` 包含 2 个元素,按主导程度排序
- [ ] 6.4 对比新旧方式提取的 `art_style` 值,分析一致性和改进情况
- [ ] 6.5 验证 CSV 输出正确展开 `art_style` 和 `art_style_raw` 字段(使用 `|` 分隔多个值)

---

## 7. 文档更新

- [x] 7.1 在 `openspec/project.md` 的"架构模式"章节补充艺术风格检测阶段说明
- [x] 7.2 创建 `src/tools/README.md`,说明艺术风格词表和分析工具的使用方式

---

## 8. 代码审查与优化

- [x] 8.1 审查 `art_style.py` 代码:
  - 确保异常处理覆盖所有 VLM 调用失败场景
  - 确保日志记录清晰(使用 `logger.info`, `logger.warning`)
  - 验证双字段输出逻辑的正确性
- [x] 8.2 审查管道集成代码:
  - 确保阶段调用顺序正确
  - 确保元数据合并逻辑不覆盖其他字段
  - 确保同时合并 `art_style` 和 `art_style_raw` 两个字段
- [x] 8.3 运行 `openspec validate extract-art-style-detection --strict` 确保提案通过验证

---

## 9. 词表演进与数据分析(长期任务)

- [x] 9.1 建立 `art_style_raw` 数据分析脚本:
  - 统计所有输出中 `art_style_raw` 的高频词汇
  - 按出现频率排序,识别 > 5% 的候选词
  - 生成统计报告(包含词频、示例图像路径)
- [ ] 9.2 每季度回顾词表:
  - 评估高频自由词是否应纳入标准词表
  - 分析"其他"类别的占比,判断词表覆盖度
  - 如有必要,更新 `docs/metadata/艺术风格词表.md`
- [ ] 9.3 词表更新后的数据迁移:
  - 重新处理历史数据中 `art_style` 为 `["其他"]` 的记录
  - 对比新旧分类结果,验证改进效果
  - 更新 CSV 导出数据

---

## 依赖关系说明

- **并行任务**: 1.1-1.2 可同时进行
- **依赖链 1**: 2.1 依赖 1.2(提示词模板)
- **依赖链 2**: 4.2 依赖 2.1(模块实现)和 3.1(配置)
- **依赖链 3**: 5.1-5.2 应在 6.1(测试验证)通过后执行,确保新模块稳定
- **最终验证**: 8.3 应在所有任务完成后执行

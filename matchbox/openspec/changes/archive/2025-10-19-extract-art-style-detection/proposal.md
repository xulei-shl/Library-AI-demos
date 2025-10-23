# 提案:提取艺术风格检测模块

## Why

当前 `art_style` 字段在事实描述阶段通过 VLM 进行随机提取,没有规范的候选词表作为约束。这导致两个问题:

1. **数据一致性差**: 不同批次的处理可能产生相似但措辞不同的艺术风格标签(例如:"木刻版画" vs "版画风格" vs "木版画")
2. **模块职责不清**: 艺术风格识别是一个相对独立的分析维度,当前耦合在事实描述阶段中,不利于未来扩展和优化

通过引入标准化的艺术风格词表并将其提取为独立模块,可以提高元数据质量和系统可维护性。

## What Changes

- 在 `docs/metadata/` 路径下新建 **《艺术风格词表.md》**,定义火花常见艺术风格的标准化分类和描述
  - 包含 13 个标准艺术风格分类(写实绘画、木刻版画、工笔画等)
  - 支持 **双字段输出**:`art_style`(规范词) + `art_style_raw`(自由词)
  - 支持 1-2 个主导风格的多风格标注
- 创建新的处理阶段模块 `src/core/stages/art_style.py`,专门负责艺术风格识别
- 从 `src/core/stages/fact_description.py` 中移除艺术风格提取逻辑
- 更新 `fact_description.md` 和 `fact_description-noseries.md` 提示词,移除艺术风格相关指令
- 新建 `src/prompts/art_style.md` 提示词模板,包含艺术风格词表约束和双字段输出指导
- 在 `config/settings.yaml` 中添加 `art_style` 任务配置
- 在 `src/core/pipeline.py` 中集成艺术风格检测阶段(在事实描述之后、功能类型之前执行)
- 更新输出 JSON schema:
  - 添加 `art_style`: `List<String> | null` - 规范化风格分类(1-2 个)
  - 添加 `art_style_raw`: `List<String> | null` - 自由描述的风格词(可选)
  - 添加 `art_style_meta`: 执行元数据

**注意**: 此变更 **扩展** 了 JSON 输出格式(从单一 `art_style` 字段变为双字段),同时提高数据质量和灵活性。

## Impact

### 受影响的规范 (Affected Specs)
- **新增**: `art-style-detection` (新能力)
- **修改**: `pipeline-orchestration` (添加新阶段)

### 受影响的代码 (Affected Code)
- `src/core/stages/fact_description.py` - 移除艺术风格提取逻辑
- `src/core/stages/art_style.py` - **新建**独立艺术风格检测模块
- `src/core/pipeline.py` - 集成新阶段到主流程
- `src/prompts/fact_description.md` - 移除艺术风格词条和输出字段
- `src/prompts/fact_description-noseries.md` - 移除艺术风格词条和输出字段
- `src/prompts/art_style.md` - **新建**艺术风格检测提示词
- `config/settings.yaml` - 添加 art_style 任务配置
- `docs/metadata/艺术风格词表.md` - **新建**标准化词表文档

### 向后兼容性
- ⚠️ **格式扩展**: JSON 输出格式从单一字段变为双字段
  - **旧格式**: `"art_style": "木刻版画"`
  - **新格式**: `"art_style": ["木刻版画"], "art_style_raw": null`
- ✅ **数据语义兼容**: `art_style` 仍表示艺术风格,但类型从 `String` 变为 `List<String>`
- ✅ **渐进式改进**: 提高数据质量和灵活性,支持多风格和词表演进
- 📋 **下游系统影响**: 需要更新 CSV 导出和数据分析脚本以处理列表类型

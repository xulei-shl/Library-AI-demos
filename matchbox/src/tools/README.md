# 工具使用说明 (Tools Usage Guide)

本目录包含用于数据分析和维护的独立工具脚本。

## 艺术风格原始数据分析工具 (Art Style Raw Data Analysis)

### 功能描述

`analyze_art_style_raw.py` 用于分析管道输出中的 `art_style_raw` 字段，识别高频自由词汇，为艺术风格词表的演进提供数据支持。

### 使用方法

#### 基本用法

```bash
python -m src.tools.analyze_art_style_raw
```

这将分析默认输出目录 (`runtime/outputs`) 中的所有 JSON 文件，并在控制台打印报告。

#### 指定输入目录

```bash
python -m src.tools.analyze_art_style_raw --input-dir /path/to/outputs
```

#### 自定义频率阈值

```bash
python -m src.tools.analyze_art_style_raw --threshold 3.0
```

默认阈值为 5.0%，即只显示出现频率 >= 5% 的候选词。

#### 保存报告到文件

```bash
python -m src.tools.analyze_art_style_raw --output runtime/reports/art_style_analysis.txt
```

#### 完整示例

```bash
python -m src.tools.analyze_art_style_raw \
  --input-dir runtime/outputs \
  --threshold 3.0 \
  --output runtime/reports/art_style_analysis_$(date +%Y%m%d).txt
```

### 输出报告内容

报告包含以下部分:

1. **统计概览**
   - 总记录数
   - 唯一艺术风格术语数
   - "其他"类别使用情况
   - 频率阈值

2. **高频候选术语**
   - 超过阈值的术语列表
   - 每个术语的出现次数和占比
   - 示例图像 ID

3. **完整术语频率分布**
   - 所有 `art_style_raw` 术语的完整列表
   - 按频率降序排列

4. **建议**
   - 推荐纳入标准词表的术语
   - 词表覆盖度评估

### 应用场景

1. **季度词表回顾**: 每季度运行分析，识别需要纳入标准词表的高频术语
2. **数据质量评估**: 检查"其他"类别的使用率，判断标准词表的覆盖度
3. **趋势分析**: 对比不同时间段的报告，识别艺术风格趋势变化

### 示例输出

```
================================================================================
艺术风格原始数据分析报告 (Art Style Raw Data Analysis Report)
================================================================================

总记录数 (Total Records): 150
唯一艺术风格术语数 (Unique Terms): 12
"其他"类别使用次数 ("Other" Category Usage): 18 (12.00%)
频率阈值 (Frequency Threshold): 5.0%

================================================================================
高频候选术语 (High-Frequency Candidate Terms, >= 5.0%)
================================================================================

术语 (Term)                    次数 (Count)      占比 (Percentage)    示例 (Examples)
--------------------------------------------------------------------------------
赛璐璐动画风格                 15                10.00%            A001, A002, A003
包豪斯设计风格                 10                 6.67%            B015, B016, B017
波普艺术风格                    8                 5.33%            C020, C021, C022

...
```

## 添加新工具

如需添加新的分析工具，请遵循以下规范:

1. 在 `src/tools/` 目录下创建新的 Python 脚本
2. 使用命令行参数 (`argparse`) 提供灵活的配置选项
3. 支持独立运行: `python -m src.tools.your_tool`
4. 在本 README 中添加使用说明
5. 在 `src/tools/__init__.py` 中导出新工具

## 维护说明

- 工具应保持独立性，不依赖主管道运行
- 所有工具应支持 `--help` 参数显示使用说明
- 输出应包含清晰的中英文说明
- 建议提供 `--output` 参数支持保存报告到文件

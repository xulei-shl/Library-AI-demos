# JSON 导出到 CSV 功能说明

## 概述

新增了独立的 JSON 到 CSV 导出模块 `src/utils/json_to_csv.py`，用于将处理后的 JSON 结果导出为 CSV 格式。

## 主要功能

1. **自动分类导出**
   - 系列 JSON（文件名以 `S_` 开头）导出到 `series_results.csv`
   - 对象 JSON（其他文件）导出到 `object_results.csv`

2. **智能字段过滤**
   - 自动过滤所有 `*_meta` 字段（如 `fact_meta`, `art_style_meta`, `type_meta` 等）
   - 自动过滤 `consensus_meta` 字段
   - 自动过滤 `reasoning` 字段

3. **Series 信息提取**
   - 对象 JSON 中的 `series` 节点会被展开
   - 只提取 `series.name` → `series_name` 列
   - 只提取 `series.id` → `series_id` 列

4. **数据类型处理**
   - 列表类型转换为 JSON 字符串
   - 字典类型转换为 JSON 字符串
   - None 值转换为空字符串
   - 添加 `_source_file` 列用于追溯源文件

## 使用方法

### 1. 在 Pipeline 中自动调用

Pipeline 在处理完成后会自动调用导出功能：

```python
from src.core.pipeline import run_pipeline

run_pipeline()
# 自动在 outputs 目录生成 series_results.csv 和 object_results.csv
```

### 2. 独立使用

可以单独运行导出功能：

```python
from src.utils.json_to_csv import export_json_to_csv

# 导出指定目录的 JSON 文件
series_count, object_count = export_json_to_csv(
    json_directory="runtime/outputs",
    series_csv_path="runtime/outputs/series_results.csv",  # 可选
    object_csv_path="runtime/outputs/object_results.csv"   # 可选
)

print(f"导出完成: 系列 {series_count} 条, 对象 {object_count} 条")
```

### 3. 命令行运行

```bash
python -m src.utils.json_to_csv <json_directory> [series_csv_path] [object_csv_path]
```

示例：
```bash
python -m src.utils.json_to_csv runtime/outputs
```

## 输出示例

### 系列 CSV (series_results.csv)

| name | manufacturer | country | theme | description | ... | _source_file |
|------|--------------|---------|-------|-------------|-----|--------------|
| 兔斯基 | 方舟名品 | 中国 | ["卡通"] | ... | ... | S_20250828_131905_consensus_test.json |

### 对象 CSV (object_results.csv)

| id | country | manufacturer | theme | ... | series_name | series_id | _source_file |
|----|---------|--------------|-------|-----|-------------|-----------|--------------|
| MVIMG_20250828_100626 | 中国 | ... | ["动漫"] | ... | 水浒人物 | NaN | MVIMG_20250828_100626.json |

## 与旧实现的区别

### 旧实现 (output_formatter.py)
- 在处理过程中收集记录
- 所有记录导出到单一 CSV (`results.csv`)
- Series 字段只保留 name

### 新实现 (json_to_csv.py)
- 处理完成后扫描 JSON 文件
- 分别导出系列和对象到不同 CSV
- Series 提取 name 和 id
- 过滤更彻底（包括 reasoning 等）

## 注意事项

1. **编码**: CSV 文件使用 `utf-8-sig` 编码，可在 Excel 中正确显示中文
2. **字段顺序**: 保持字段出现的顺序（而非排序）
3. **文件追溯**: `_source_file` 列记录了源 JSON 文件名，便于调试
4. **递归扫描**: 会递归扫描目录下的所有 JSON 文件

# Excel文件路径配置优化说明

## 修改背景

之前的配置存在以下问题：
- `config/setting.yaml` 中只有 `input_image_dir: data` 这样的文件夹路径
- 代码中通过硬编码文件名（如 "月归还.xlsx"、"近三月借阅.xlsx"）来读取具体文件
- 无法灵活配置不同的Excel文件路径
- `input_image_dir` 配置实际上没有被任何代码使用，造成配置冗余

## 优化方案

### 1. 配置文件修改

在 `config/setting.yaml` 中新增了 `excel_files` 配置段，并移除了无用的 `input_image_dir`：

```yaml
paths:
  outputs_dir: runtime/outputs
  logs_dir: runtime/logs
  
  # Excel数据文件路径配置
  excel_files:
    # 月归还数据文件路径
    monthly_return_file: "data/月归还.xlsx"
    # 近三月借阅数据文件路径
    recent_three_months_borrowing_file: "data/近三月借阅.xlsx"
```

### 2. 配置读取工具修改

在 `src/utils/config_utils.py` 中：
- 新增了对Excel文件路径配置的支持
- `get_paths_config()` 方法返回包含两个Excel文件路径的完整配置
- 移除了对无用 `input_image_dir` 的引用

### 3. 数据加载器修改

在 `src/core/data_loader.py` 中：
- `load_monthly_return_data()` 和 `load_recent_three_months_borrowing_data()` 函数新增可选参数
- 当不传入文件路径参数时，自动从配置文件读取对应路径
- 保持向后兼容性，仍支持手动传入文件路径

## 使用方式

### 方式1：从配置文件读取（推荐）

```python
# 自动从配置文件读取路径
monthly_data = load_monthly_return_data()
borrowing_data = load_recent_three_months_borrowing_data()
```

### 方式2：手动指定文件路径

```python
# 手动指定文件路径（保持向后兼容）
monthly_data = load_monthly_return_data("custom/month_return.xlsx")
borrowing_data = load_recent_three_months_borrowing_data("custom/borrowing_data.xlsx")
```

### 方式3：通过配置类读取

```python
from src.utils.config_utils import config

# 获取完整路径配置
paths_config = config.get_paths_config()
monthly_file = paths_config['monthly_return_file']
borrowing_file = paths_config['recent_three_months_borrowing_file']

# 直接读取特定配置
monthly_file = config.get('paths.excel_files.monthly_return_file')
borrowing_file = config.get('paths.excel_files.recent_three_months_borrowing_file')
```

## 配置灵活性

现在可以轻松配置不同位置的Excel文件：

```yaml
# 示例1：使用不同文件夹
excel_files:
  monthly_return_file: "data/2025-09/月归还.xlsx"
  recent_three_months_borrowing_file: "data/2025-09/近三月借阅.xlsx"

# 示例2：使用完全不同的路径
excel_files:
  monthly_return_file: "/absolute/path/to/target_file.xlsx"
  recent_three_months_borrowing_file: "different_folder/borrowing_file.xlsx"

# 示例3：使用相对路径
excel_files:
  monthly_return_file: "../external_data/target.xlsx"
  recent_three_months_borrowing_file: "subfolder/borrowing.xlsx"
```

## 测试验证

所有修改已经过测试验证：

1. **配置读取测试**：✅ 成功读取新的Excel文件路径配置
2. **数据加载测试**：✅ 成功从配置路径加载两个Excel文件
3. **统计功能测试**：✅ 统计模块正常工作
4. **配置清理验证**：✅ 移除无用配置后系统运行正常

## 向后兼容性

- 所有现有的API保持不变
- 原有代码无需修改即可继续工作
- 新增的灵活性是可选的，不会破坏现有功能

## 清理优化

在本次优化中，还清理了以下冗余配置：
- 移除了无实际用途的 `input_image_dir: data` 配置
- 删除了 `config_utils.py` 中对该无用配置的引用
- 简化了 `get_paths_config()` 的返回值

## 优势

1. **灵活性**：可以配置任意路径的Excel文件
2. **易维护**：配置集中管理，修改无需改动代码
3. **可扩展**：未来可以轻松添加更多文件配置
4. **向后兼容**：不破坏现有代码结构
5. **简洁性**：移除冗余配置，配置更加清晰

## 总结

通过这次优化，系统现在支持灵活配置Excel文件路径，摆脱了硬编码文件名的限制，大大提升了系统的可配置性和易维护性。同时清理了冗余配置，使配置文件更加简洁清晰。
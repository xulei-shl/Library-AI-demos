# Excel 数据自动合并系统

## 简介

这是一个强大的 Python 脚本系统，旨在自动化多个 Excel 文件的数据合并过程。它支持智能文件识别、灵活的配置选项以及详细的日志记录，确保数据处理的准确性和高效性。

## 功能特性

- 🔄 **自动文件识别**: 自动扫描指定目录下的所有 Excel 文件。
- 🎯 **智能处理策略**: 根据文件名自动选择对应的处理策略（如一部、二部、三部文件）。
- 📋 **智能 Sheet 选择**: 自动选择最优工作表（优先级：业务表 > Sheet1 > 第一个 sheet）。
- ✅ **表头验证**: 自动验证 Excel 表头与目标文件匹配，不匹配则跳过处理。
- 📊 **列对齐合并**: 按列名匹配数据，自动对齐到目标文件结构。
- 🕒 **时间筛选**: 支持按业务时间筛选当年当月数据（可配置）。
- 🔄 **列名映射**: 支持特定文件的列名重命名和动态列名匹配（高度可配置）。
- 📁 **文件管理**: 处理完成后自动移动文件到“已处理”文件夹。
- 📝 **详细日志**: 提供完整的处理日志和错误追踪。
- 🔒 **幂等性**: 支持重复运行，不会重复处理已处理的文件。
- 📈 **统计分析**: 可选的统计分析模块，用于生成数据报告。

## 系统要求

- Python 3.7+
- pandas >= 2.0.0
- openpyxl >= 3.1.0

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

1.  将需要处理的 Excel 文件放置在 `SOURCE_EXCEL_PATH` 配置的目录下。
2.  确保 `TARGET_FILE_PATH` 配置的目标文件存在且可访问。
3.  运行主程序：

    ```bash
    python main.py
    ```

## 配置说明

所有核心配置参数都集中在 `src/config/settings.py` 文件中，您可以根据需求进行修改。

### 路径配置

-   `TARGET_FILE_PATH`: 目标 Excel 文件的绝对路径。
    ```python
    TARGET_FILE_PATH = r"E:\\Desk\\excel-merge-0.2\\2025年度业务统计表.xlsx"
    ```
-   `SOURCE_EXCEL_PATH`: 源 Excel 文件所在的目录的绝对路径。
    ```python
    SOURCE_EXCEL_PATH = r"E:\\Desk\\excel-merge-0.2\\1"
    ```
-   `PROCESSED_FOLDER`: 已处理文件移动到的目录的绝对路径。
    ```python
    PROCESSED_FOLDER = r"E:\\Desk\\excel-merge-0.2\\已处理"
    ```
-   `LOG_FOLDER`: 日志文件存储的目录（相对于项目根目录）。
    ```python
    LOG_FOLDER = "logs"
    ```

### 文件识别配置

-   `FILE_PATTERNS`: 定义不同文件类型的识别关键词。系统会根据文件名是否包含这些关键词来应用不同的处理策略。
    ```python
    FILE_PATTERNS = {
        'yibu': '馆藏业务统计表',
        'erbu': '二部',
        'sanbu': '三部'
    }
    ```

### 列映射配置

-   `COLUMN_MAPPINGS`: 定义列名的静态映射规则。系统优先采用“默认直通”逻辑，此配置仅用于处理需要转换或有别名的列。支持全局 (`"*"`) 和特定文件类型（如 `'yibu'`, `'erbu'`, `'sanbu'`）的映射。
    ```python
    COLUMN_MAPPINGS = {
        # 默认映射规则，仅配置需要转换或有别名的列
        "*": {  
            "统计员": "统计人",
            "移库来源": "上游来源",
            "移库去向": "下游去向",
        },
        # 针对 "一部" 的特殊规则
        'yibu': {
            # "旧列名": "新列名"
        },
    }
    ```
-   `DYNAMIC_COLUMN_PATTERNS`: 定义动态列名映射规则，使用正则表达式匹配列名。同样支持全局 (`"*"`) 和特定文件类型。
    ```python
    DYNAMIC_COLUMN_PATTERNS = {
        "*": {
            r'^\d+$': 'I',  # 匹配纯数字列名（如168690等动态计算的数字）
        },
        'erbu': {
            # 二部特定的动态模式
        },
    }
    ```

### 缺失列默认值配置

-   `DEFAULT_VALUES`: 当源文件缺失目标列时，用于填充的默认值。支持全局 (`"*"`) 和特定文件类型。
    ```python
    DEFAULT_VALUES = {
        "*": {
            # "目标列名": "默认值"
            # 例如: "单位": "册"
        },
        'sanbu': {
            "统计人": "孙超",
            "单位": "册件"
        }
    }
    ```

### 数据处理配置

-   `DATA_PROCESSING_CONFIG`: 控制数据清洗、空行移除、时间筛选等行为。支持全局 (`"*"`) 和特定文件类型。
    ```python
    DATA_PROCESSING_CONFIG = {
        "*": {
            "enable_default_cleaning": True,  # 是否启用默认数据清洗
            "remove_empty_rows": True,        # 是否移除空行
            "remove_whitespace_rows": True,   # 是否移除空白字符行
        },
        'erbu': {
            "enable_time_filtering": True,    # 是否启用时间筛选
            "filter_target_month": "last",   # 筛选目标月份：“last”表示上个月
        },
        'sanbu': {
            "apply_default_values": True,     # 是否应用默认值填充
        }
    }
    ```

### Excel 处理配置

-   `EXCEL_SHEET_NAME`: 默认的 Excel 工作表名称。
    ```python
    EXCEL_SHEET_NAME = '业务表'
    ```
-   `SHEET_PRIORITY`: Sheet 选择优先级列表。系统会按照列表顺序查找并使用第一个存在的 Sheet。
    ```python
    SHEET_PRIORITY = ['业务表', 'Sheet1']
    ```
-   `BUSINESS_TIME_COLUMN`: 业务时间列的名称。
    ```python
    BUSINESS_TIME_COLUMN = '业务时间'
    ```
-   `BUSINESS_TIME_FORMAT`: 业务时间列的日期格式。
    ```python
    BUSINESS_TIME_FORMAT = '%Y年%-m月'
    ```

### 日志配置

-   `LOG_LEVEL`: 日志输出级别（如 `'INFO'`, `'DEBUG'`, `'WARNING'`, `'ERROR'`）。
    ```python
    LOG_LEVEL = 'INFO'
    ```
-   `LOG_FORMAT`: 日志消息的格式。
    ```python
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ```
-   `LOG_DATE_FORMAT`: 日志中时间戳的格式。
    ```python
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    ```

### 性能配置

-   `CHUNK_SIZE`: 大文件分块处理的大小（行数）。
    ```python
    CHUNK_SIZE = 10000
    ```
-   `MAX_RETRY_TIMES`: 文件操作失败时的最大重试次数。
    ```python
    MAX_RETRY_TIMES = 3
    ```
-   `RETRY_DELAY`: 重试之间的延迟秒数。
    ```python
    RETRY_DELAY = 1
    ```

### 统计分析配置

-   `STATISTICS_CONFIG`: 统计分析模块的详细配置。
    ```python
    STATISTICS_CONFIG = {
        'enabled': True,                     # 是否启用统计分析
        'target_column': '168690',           # 目标列名
        'target_column_letter': 'I',         # 目标列字母
        'group_by_column': '馆藏编号',         # 分组列名
        'business_time_column': '业务时间',     # 业务时间列名
        'output_file_path': r"E:\\Desk\\excel-merge\\已处理\\馆藏量统计动态表-2025.xlsx", # 统计结果输出文件路径
        'output_sheet_name': '业务表',         # 统计结果输出工作表名称
        'output_columns': {                  # 输出列映射
            'group_column': 'A',
            'sum_column': 'B',
            'time_column': 'C'
        }
    }
    ```

## 处理规则

### 文件类型识别

系统会根据 `FILE_PATTERNS` 中定义的关键词自动识别处理类型，并应用相应的处理策略。

### 智能 Sheet 选择机制

系统采用智能算法自动选择最合适的工作表：

#### 选择优先级

1.  **单 Sheet 文件**: 直接使用唯一的工作表。
2.  **多 Sheet 文件**: 按照 `SHEET_PRIORITY` 配置的顺序查找，如果找到则使用。
3.  **兜底策略**: 如果 `SHEET_PRIORITY` 中的 Sheet 都不存在，则使用第一个工作表。

#### 表头验证机制

每个选定的工作表都会进行严格的表头验证：

1.  **读取表头**: 获取选定 Sheet 的所有列名。
2.  **应用映射**: 根据文件类型应用 `COLUMN_MAPPINGS` 和 `DYNAMIC_COLUMN_PATTERNS` 中定义的列名映射规则。
3.  **完全匹配**: 与目标文件表头进行完全一致性验证。
4.  **处理决策**:
    -   ✅ 匹配成功：继续处理该文件。
    -   ❌ 匹配失败：记录详细日志并跳过该文件。

### 列名映射机制

系统支持智能列名映射，优先采用“默认直通”逻辑，即如果源文件和目标文件的列名相同，则无需显式配置，系统能自动将其复制过去。只有当列名需要转换或有别名时，才需要进行特殊配置。

-   **默认直通**: 如果源列名与目标列名一致，系统将直接复制该列数据，无需额外配置。
-   **静态映射**: 通过 `COLUMN_MAPPINGS` 配置，将源文件中的特定列名映射为目标文件所需的列名。此配置具有更高优先级，可覆盖默认直通逻辑，用于处理需要转换或有别名的列。
-   **动态映射**: 通过 `DYNAMIC_COLUMN_PATTERNS` 配置，使用正则表达式匹配源文件中的列名，并将其映射为目标列名。这对于处理不规则或动态生成的列名非常有用。

### 缺失列默认值机制

如果源文件中缺少目标文件所需的某些列，系统会根据 `DEFAULT_VALUES` 配置自动填充默认值，确保数据完整性。

### 数据处理流程

1.  **文件扫描**: 扫描 `SOURCE_EXCEL_PATH` 目录下的所有 Excel 文件。
2.  **类型识别**: 根据文件名识别处理类型。
3.  **智能 Sheet 选择**: 按优先级自动选择最优工作表。
4.  **表头验证**: 验证表头匹配性（含列名映射）。
5.  **数据读取**: 读取验证通过的 Excel 数据。
6.  **数据处理**: 应用 `DATA_PROCESSING_CONFIG` 中定义的处理策略（如数据清洗、时间筛选、默认值填充）。
7.  **列对齐**: 按目标文件的列结构对齐数据。
8.  **数据合并**: 合并所有处理后的数据。
9.  **格式转换**: 将业务时间列转换为 `BUSINESS_TIME_FORMAT` 定义的格式。
10. **数据追加**: 追加到目标文件末尾。
11. **文件移动**: 移动已处理文件到 `PROCESSED_FOLDER`。
12. **统计分析 (可选)**: 如果 `STATISTICS_CONFIG` 启用，则进行统计分析并输出结果。

## 日志系统

-   日志文件保存在 `LOG_FOLDER` 目录下。
-   按日期命名：`excel_merge_YYYYMMDD.log`。
-   同时输出到控制台和文件。
-   包含详细的处理过程和错误信息。

## 错误处理

系统具备完善的错误处理机制：

-   文件访问异常处理。
-   数据格式验证。
-   自动重试机制（可配置 `MAX_RETRY_TIMES` 和 `RETRY_DELAY`）。
-   详细的错误日志记录。

## 注意事项

1.  确保目标 Excel 文件存在且未被其他程序占用。
2.  源 Excel 文件的表头必须与目标文件完全匹配（考虑列名映射和动态列名匹配）。
3.  系统会自动选择最优工作表，无需手动指定 Sheet 名称。
4.  表头验证失败的文件会被自动跳过，详细信息记录在日志中。
5.  业务时间列应为有效的日期格式。
6.  建议在处理前备份重要数据。

## 故障排除

### 常见问题

1.  **文件被占用**: 确保 Excel 文件未在其他程序中打开。
2.  **权限不足**: 确保对目标文件路径有读写权限。
3.  **数据格式错误**: 检查 Excel 文件格式和数据完整性。
4.  **表头验证失败**:
    -   检查源文件表头是否与目标文件匹配。
    -   确认是否需要配置列名映射规则或动态列名匹配规则。
    -   查看日志了解具体的不匹配列名。
5.  **Sheet 选择问题**:
    -   系统会自动选择最优 Sheet，无需手动干预。
    -   如需调整优先级，可修改 `SHEET_PRIORITY` 配置。
6.  **列名映射不生效**:
    -   确认文件名包含正确的识别关键词。
    -   检查 `COLUMN_MAPPINGS` 和 `DYNAMIC_COLUMN_PATTERNS` 配置是否正确。

### 查看日志

详细的执行日志保存在 `logs/` 目录下，可以查看具体的错误信息和处理过程。

## 目录结构

```
excel-merge/
├── main.py                    # 主程序入口
├── requirements.txt           # 依赖包列表
├── README.md                  # 说明文档
├── src/                       # 源代码目录
│   ├── processors/            # 处理器模块
│   ├── core/                  # 核心服务模块
│   ├── utils/                 # 工具模块
│   └── config/                # 配置模块
├── logs/                      # 日志文件目录
├── 已处理/                    # 已处理文件目录
└── docs/                      # 文档目录
    └── changelogs/            # 变更日志
```

## 版本信息

-   版本: 1.2.0
-   最新更新: 2025年9月11日
-   主要更新:
    -   ✨ 增强配置化能力，支持更多自定义选项。
    -   ✅ 优化表头验证和列名映射机制。
    -   📈 新增可选的统计分析模块。
    -   🔧 完善数据处理流程和错误处理。
-   作者: CodeBuddy

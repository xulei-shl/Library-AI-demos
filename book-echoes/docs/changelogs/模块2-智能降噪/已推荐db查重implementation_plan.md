# 数据库查重过滤器实现计划

## 目标

在 `src/core/filters` 的数据过滤逻辑中新增数据库查重功能,使用Excel的`书目条码`与数据库表`recommendation_results`查重,将"人工评选"结果为`通过`的数据单独保存为Excel,并在后续流程中过滤掉这些已入选书目。

## 实现方案

### 1. 创建数据库查重过滤器

**文件**: `src/core/filters/db_duplicate_filter.py`

**功能**:
- 从配置文件读取数据库路径
- 连接SQLite数据库
- 批量查询`recommendation_results`表
- 根据`manual_selection='通过'`条件过滤数据
- 返回查重结果和统计信息

**关键方法**:
- `__init__`: 初始化数据库连接配置
- `_connect_database`: 建立数据库连接
- `_batch_query_duplicates`: 批量查询已入选书目
- `apply`: 实现过滤逻辑(继承自BaseFilter)

### 2. 注册新过滤器

**文件**: `src/core/filters/__init__.py`

**修改**:
- 在`FilterRegistry`中注册`db_duplicate`类型过滤器

### 3. 配置文件更新

**文件**: `config/setting.yaml`

**新增配置**:
```yaml
filtering:
  rule_db_duplicate:
    enabled: true
    description: "数据库查重-过滤已入选书目"
    target_column: "书目条码"
    db_table: "recommendation_results"
    db_column: "barcode"
    filter_condition:
      column: "manual_selection"
      value: "通过"
```

### 4. 修改数据过滤器

**文件**: `src/core/data_filter.py`

**修改**:
- 在`_determine_filter_type`方法中添加`db_duplicate`类型识别
- 在`filter_books`方法中支持数据库查重结果的单独跟踪
- 返回值中增加数据库查重结果数据

### 5. 修改结果导出器

**文件**: `src/core/result_exporter.py`

**新增方法**:
- `export_db_duplicate_data`: 导出数据库查重结果到独立Excel

### 6. 修改主流程

**文件**: `main.py`

**修改**:
- 在`export_filtered_results`函数中新增第3个Excel导出
- 文件名格式: `数据库查重结果_YYYYMMDD_HHMMSS.xlsx`

## 实现细节

### 数据库查询逻辑

```python
# 批量查询已入选书目
SELECT barcode 
FROM recommendation_results 
WHERE manual_selection = '通过'
AND barcode IN (条码列表)
```

### 过滤器执行顺序

建议将数据库查重过滤器放在**第一位**执行,原因:
1. 已入选书目无需执行后续过滤逻辑
2. 减少不必要的计算开销
3. 提高整体性能

### Excel输出格式

**数据库查重结果Excel**包含:
- 原始数据的所有列
- 新增列: `查重原因` - 标注为"已在评选中入选"
- 新增列: `查重时间` - 记录查重时间戳
- 工作表1: 查重数据
- 工作表2: 查重信息(统计、配置等)

### 错误处理

1. **数据库不存在**: 记录警告,跳过查重,不影响其他过滤器
2. **数据库连接失败**: 降级处理,记录错误日志
3. **表不存在**: 记录警告,跳过查重
4. **列名不匹配**: 尝试自动映射(书目条码/barcode等)

## 验证计划

### 单元测试场景

1. 数据库存在且有匹配数据
2. 数据库存在但无匹配数据
3. 数据库不存在
4. 数据库连接失败
5. 列名映射测试

### 集成测试

1. 完整流程测试: 模块1 → 数据库查重 → 其他过滤器
2. 验证3个Excel文件正确生成
3. 验证数据一致性(查重数据+被过滤数据+筛选结果 = 原始数据)

## 文件清单

### 新增文件
- [NEW] [db_duplicate_filter.py](file:///f:/Github/Library-AI-demos/book-echoes/src/core/filters/db_duplicate_filter.py)

### 修改文件
- [MODIFY] [__init__.py](file:///f:/Github/Library-AI-demos/book-echoes/src/core/filters/__init__.py)
- [MODIFY] [setting.yaml](file:///f:/Github/Library-AI-demos/book-echoes/config/setting.yaml)
- [MODIFY] [data_filter.py](file:///f:/Github/Library-AI-demos/book-echoes/src/core/data_filter.py)
- [MODIFY] [result_exporter.py](file:///f:/Github/Library-AI-demos/book-echoes/src/core/result_exporter.py)
- [MODIFY] [main.py](file:///f:/Github/Library-AI-demos/book-echoes/main.py)

## 实现顺序

1. ✅ 创建实现计划文档
2. ⏳ 创建数据库查重过滤器类
3. ⏳ 注册过滤器到FilterRegistry
4. ⏳ 更新配置文件
5. ⏳ 修改数据过滤器支持新过滤器
6. ⏳ 修改结果导出器添加新导出方法
7. ⏳ 修改主流程添加第3个Excel导出
8. ⏳ 测试验证

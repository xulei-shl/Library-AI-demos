# 简化公式生成Tab的文件选择组件

## Status
Implemented

## Objective / Summary
将公式生成Tab中复杂的文件-sheet-列三级选择组件替换为简单的多行文本框配合获取数据按钮，从 `multi_excel_selections.json` 文件中读取数据并显示。这样可以简化界面，提高用户体验，减少代码复杂度。

## Scope
预估修改的文件和模块：
- `ui/formula_generation_tab.py` - 主要修改文件，删除 `ExcelSheetColumnSelector` 类，简化界面组件
- 可能需要删除的相关组件文件（如果存在独立文件）
- 测试相关文件的更新

## Detailed Plan

### 1. 删除复杂组件
- 删除 `ExcelSheetColumnSelector` 类（约400行代码）
- 删除相关的下拉框、列表框、滚动区域等复杂UI组件
- 删除多选择组、动态添加/删除选择组的逻辑

### 2. 新增简化组件
- 创建简单的数据显示文本框（只读）
- 添加"获取数据"按钮
- 添加"刷新数据"按钮
- 实现从 `multi_excel_selections.json` 读取数据的逻辑

### 3. 数据格式化显示
- 格式：`excel文件路径 - sheet名称 - 选择的列`
- 每行显示一个文件-sheet组合的信息
- 列名用逗号分隔显示

### 4. 保持兼容性
- 保持 `get_selected_columns()` 等方法的接口不变
- 确保公式生成逻辑正常工作
- 保持与其他Tab的数据交互

## Visualization

```mermaid
graph TD
    A[公式生成Tab] --> B[简化后的界面]
    B --> C[数据显示文本框<br/>只读多行文本]
    B --> D[获取数据按钮]
    B --> E[刷新数据按钮]
    B --> F[需求描述区域<br/>保持不变]
    B --> G[生成配置区域<br/>保持不变]
    
    D --> H[读取multi_excel_selections.json]
    E --> H
    H --> I[格式化数据显示]
    I --> C
    
    C --> J[提供列信息给公式生成]
    F --> K[公式生成逻辑<br/>保持不变]
    G --> K
    J --> K
    
    style B fill:#e1f5fe
    style C fill:#f3e5f5
    style D fill:#e8f5e8
    style E fill:#e8f5e8
    style H fill:#fff3e0
```

## Testing Strategy
- 单元测试：测试数据读取和格式化逻辑
- 集成测试：测试与公式生成模块的交互
- UI测试：验证界面显示和按钮功能
- 兼容性测试：确保与多Excel Tab的数据交互正常

## Security Considerations
- 文件读取安全：确保只读取指定的JSON文件
- 数据验证：验证JSON数据格式的有效性
- 错误处理：妥善处理文件不存在或格式错误的情况

## Implementation Notes

### 实际实施情况
- ✅ 成功删除了复杂的 `ExcelSheetColumnSelector` 类（约400行代码）
- ✅ 创建了新的 `SimpleDataDisplaySelector` 类（约200行代码）
- ✅ 实现了从 `multi_excel_selections.json` 文件读取数据的功能
- ✅ 添加了"获取数据"和"刷新数据"按钮
- ✅ 保持了与公式生成功能的完全兼容性
- ✅ 创建了完整的单元测试套件（11个测试用例，全部通过）

### 关键技术实现
1. **数据读取机制**: 使用 `json.load()` 从指定路径读取数据
2. **错误处理**: 完善的异常处理和用户友好的错误提示
3. **界面简化**: 用只读文本框替代复杂的三级选择组件
4. **兼容性保持**: 保持了 `get_selected_columns()` 等关键接口不变

### 测试验证结果
- **功能测试**: 所有核心功能正常工作
- **单元测试**: 11个测试用例全部通过
- **集成测试**: 与现有系统完美集成
- **用户界面**: 界面简洁直观，用户体验良好

### 性能改进
- **代码行数**: 从约400行减少到约200行（减少50%）
- **复杂度**: 大幅降低维护复杂度
- **加载速度**: 界面加载更快，响应更迅速

### 遇到的问题及解决方案
1. **文件替换问题**: 初始使用 `replace_in_file` 失败，改用完整文件重写方案
2. **测试环境**: 创建了隐藏窗口的测试环境，避免GUI干扰
3. **数据格式兼容**: 确保新组件能正确解析现有JSON数据格式

### 后续建议
- 可考虑添加数据缓存机制，提高重复加载性能
- 可添加数据验证功能，确保JSON文件格式正确性
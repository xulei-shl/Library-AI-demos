# MD文档处理功能架构设计

## 1. 总体架构概览

### 1.1 设计目标
- 扩展现有RSS文章处理系统，支持本地MD文档处理
- 保持与现有流程的完全兼容性
- 提供统一的Excel输出格式
- 支持渐进式处理（过滤->总结->分析）

### 1.2 核心流程对比

**现有RSS流程：**
```
RSS获取 -> 全文解析 -> 文章过滤 -> 文章总结 -> 深度分析 -> 交叉分析
```

**新增MD文档流程：**
```
MD文档读取 -> Excel生成 -> 文章过滤 -> 文章总结 -> 深度分析 -> 交叉分析
```

## 2. 核心组件设计

### 2.1 MDReader类
**位置：** `src/core/md_reader.py`

**功能：**
- 扫描指定路径下的所有.md文件
- 从文件名提取标题（去除.md扩展名）
- 读取文件内容作为全文
- 转换为标准文章数据结构

**核心方法：**
```python
class MDReader:
    def scan_directory(self, base_path: str, recursive: bool = True) -> List[Dict]:
        """扫描目录下的所有MD文件"""
        
    def extract_title_from_filename(self, filename: str) -> str:
        """从文件名提取标题"""
        
    def read_markdown_content(self, filepath: str) -> str:
        """读取MD文件内容"""
        
    def convert_to_article_structure(self, md_files: List[Dict]) -> List[Dict]:
        """转换为标准文章数据结构"""
```

### 2.2 扩展StorageManager
**新增方法：**
```python
class StorageManager:
    def save_md_results(self, articles: List[Dict], output_filename: str = None) -> str:
        """保存MD文档处理结果到Excel"""
        
    def append_md_analysis_results(self, articles: List[Dict], input_file: str) -> str:
        """追加MD文档分析结果到现有Excel"""
```

### 2.3 交互界面改造
**修改main.py中的interactive_mode()：**

原选项4：
```
4. 文章过滤 (filter) - 根据规则过滤文章
```

新子菜单结构：
```
4. 文章过滤 (filter) - 根据规则过滤文章
   4.1 RSS文章过滤 - 处理RSS源获取的文章
   4.2 MD文档处理 - 处理本地MD文档
```

## 3. 数据结构设计

### 3.1 MD文档转换后的文章结构
```python
{
    "title": "从文件名提取的标题",
    "content": "MD文件完整内容",
    "full_text": "MD文件完整内容",  # 兼容字段
    "source": "本地MD文档",
    "url": "",  # MD文档无URL
    "publish_date": "",  # 可选：从文件名或内容提取
    "author": "",  # 可选
    # 以下字段由后续处理步骤填充
    "filter_status": "",
    "filter_pass": False,
    "filter_reason": "",
    "llm_score": 0,
    "llm_summary": "",
    "llm_analysis": ""
}
```

### 3.2 Excel输出格式
**基础列：**
- filename: MD文件名
- title: 文章标题
- content: 完整内容
- source: 数据来源标识

**处理结果列：**
- filter_status: 过滤状态
- filter_pass: 是否通过过滤
- filter_reason: 过滤理由
- llm_score: LLM评分
- llm_summary: 文章摘要
- llm_analysis: 深度分析结果

## 4. 处理流程设计

### 4.1 MD文档处理完整流程
```
用户选择"4.2 MD文档处理"
    ↓
提示输入MD文档路径
    ↓
MDReader扫描并读取所有.md文件
    ↓
转换为标准数据结构
    ↓
生成Excel文件："文章汇总分析_时间戳.xlsx"
    ↓
执行文章过滤（从Excel读取数据）
    ↓
后续步骤：总结、分析等（可选）
```

### 4.2 错误处理策略
- **文件读取失败**：记录错误日志，跳过该文件，继续处理其他文件
- **Excel生成失败**：提示用户检查路径权限，提供重试选项
- **数据转换错误**：使用安全的默认值，确保流程不中断

## 5. 配置系统扩展

### 5.1 新增配置文件项
**config/subject_bibliography.yaml 新增：**
```yaml
# MD文档处理配置
md_processing:
  # 默认MD文档路径
  default_base_path: "data/md_documents"
  # 是否递归扫描子目录
  recursive_scan: true
  # Excel文件命名规则
  excel_filename_pattern: "文章汇总分析_{timestamp}"
  # 支持的文件扩展名
  supported_extensions: [".md", ".markdown"]
  # 标题提取规则
  title_extraction:
    # 是否去除文件扩展名
    remove_extension: true
    # 标题清理规则（去除特殊字符等）
    cleanup_rules: true
```

## 6. 兼容性保证

### 6.1 向后兼容
- 现有RSS处理流程完全不受影响
- 现有命令行参数和交互选项保持不变
- 现有配置文件格式向后兼容

### 6.2 渐进式升级
- 用户可以选择性地使用新功能
- 旧数据文件继续可用
- 新旧功能可以混合使用

## 7. 实施计划

### 7.1 第一阶段：核心功能
1. 创建MDReader类
2. 扩展StorageManager
3. 实现Excel生成和追加功能

### 7.2 第二阶段：用户界面
1. 修改交互菜单
2. 添加路径配置功能
3. 集成错误处理

### 7.3 第三阶段：流程集成
1. 集成到pipeline架构
2. 添加配置支持
3. 完善测试和文档

## 8. 测试策略

### 8.1 单元测试
- MDReader文件扫描和读取功能
- 数据结构转换正确性
- Excel生成和追加功能

### 8.2 集成测试
- 完整MD处理流程测试
- 与现有RSS流程的兼容性测试
- 错误场景处理测试

### 8.3 用户验收测试
- 交互界面易用性
- 配置灵活性
- 性能表现

## 9. 风险评估与缓解

### 9.1 技术风险
- **风险**：大文件MD文档处理可能导致内存问题
- **缓解**：实现分块读取和流式处理

### 9.2 用户体验风险
- **风险**：新功能增加界面复杂度
- **缓解**：保持清晰的菜单层次，提供详细的帮助信息

### 9.3 数据完整性风险
- **风险**：Excel操作可能出现数据丢失
- **缓解**：实现原子性操作，提供备份机制

## 10. 性能优化

### 10.1 文件处理优化
- 并行读取多个MD文件
- 智能缓存机制
- 增量处理支持

### 10.2 Excel操作优化
- 批量写入减少I/O操作
- 内存友好的大数据集处理
- 进度显示和取消支持

这个架构设计确保了新功能能够无缝集成到现有系统中，同时提供了良好的用户体验和数据完整性保证。
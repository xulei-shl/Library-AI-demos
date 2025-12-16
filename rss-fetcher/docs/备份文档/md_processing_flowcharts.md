# MD文档处理功能流程图

## 系统整体架构图

```mermaid
graph TB
    A[用户交互界面] --> B[主菜单选择]
    B --> C[4.1 RSS文章过滤]
    B --> D[4.2 MD文档处理]
    
    C --> E[现有RSS流程]
    E --> F[读取RSS Excel文件]
    F --> G[执行文章过滤]
    G --> H[后续处理步骤]
    
    D --> I[MD文档处理流程]
    I --> J[输入MD文档路径]
    J --> K[扫描MD文件]
    K --> L[读取文件内容]
    L --> M[转换为标准结构]
    M --> N[生成Excel文件]
    N --> O[执行文章过滤]
    O --> P[后续处理步骤]
    
    P --> Q[Excel结果输出]
    H --> Q
    
    subgraph "核心组件"
        R[MDReader类]
        S[扩展StorageManager]
        T[修改Pipeline]
        U[交互界面改造]
    end
    
    I -.-> R
    I -.-> S
    I -.-> T
    I -.-> U
```

## MD文档处理详细流程图

```mermaid
flowchart TD
    A[用户选择4.2 MD文档处理] --> B[提示输入文档路径]
    B --> C{验证路径是否存在}
    
    C -->|路径无效| D[显示错误信息]
    D --> B
    
    C -->|路径有效| E[扫描MD文件]
    E --> F[过滤.md和.markdown文件]
    F --> G{找到MD文件?}
    
    G -->|未找到| H[显示提示信息]
    H --> I[返回主菜单]
    
    G -->|找到文件| J[逐个读取MD文件]
    J --> K[提取文件名作为标题]
    K --> L[读取文件内容]
    L --> M[构建文章数据结构]
    M --> N{所有文件处理完成?}
    
    N -->|否| J
    N -->|是| O[生成Excel文件]
    O --> P[文件名: 文章汇总分析_时间戳.xlsx]
    P --> Q[保存基础数据到Excel]
    Q --> R[执行文章过滤]
    R --> S[从Excel读取数据]
    S --> T[调用LLM进行过滤]
    T --> U[更新Excel中的过滤结果]
    U --> V{是否继续后续处理?}
    
    V -->|是| W[执行文章总结]
    V -->|否| X[处理完成]
    
    W --> Y[更新Excel总结结果]
    Y --> Z{是否执行深度分析?}
    
    Z -->|是| AA[执行深度分析]
    Z -->|否| X
    
    AA --> BB[更新Excel分析结果]
    BB --> X
    
    subgraph "错误处理"
        CC[文件读取失败]
        DD[Excel写入失败]
        EE[LLM处理失败]
    end
    
    J -.-> CC
    O -.-> DD
    R -.-> EE
    
    CC --> FF[记录错误日志]
    DD --> GG[提示用户检查权限]
    EE --> HH[使用默认结果]
    
    FF --> II[继续处理其他文件]
    GG --> JJ[提供重试选项]
    HH --> KK[标记处理失败]
```

## 数据流图

```mermaid
flowchart LR
    subgraph "输入层"
        A[MD文档文件]
        B[配置文件]
    end
    
    subgraph "处理层"
        C[MDReader扫描]
        D[数据结构转换]
        E[Excel生成]
        F[LLM处理]
        G[结果追加]
    end
    
    subgraph "输出层"
        H[Excel文件]
        I[日志文件]
    end
    
    A --> C
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    C --> I
    D --> I
    E --> I
    F --> I
    G --> I
    
    subgraph "数据结构转换"
        J[文件名] --> K[标题]
        L[文件内容] --> M[全文内容]
        N[默认字段] --> O[标准字段]
    end
    
    D --> J
    D --> L
    D --> N
    J --> K
    L --> M
    N --> O
```

## Excel数据结构图

```mermaid
graph TB
    subgraph "Excel表格结构"
        A[filename - MD文件名]
        B[title - 文章标题]
        C[content - 完整内容]
        D[source - 数据来源]
        
        E[filter_status - 过滤状态]
        F[filter_pass - 是否通过]
        G[filter_reason - 过滤理由]
        
        H[llm_score - LLM评分]
        I[llm_summary - 文章摘要]
        J[llm_analysis - 深度分析]
        
        K[publish_date - 发布日期]
        L[author - 作者]
        M[tags - 标签]
    end
    
    subgraph "处理阶段"
        N[初始写入阶段]
        O[过滤处理阶段]
        P[总结处理阶段]
        Q[分析处理阶段]
    end
    
    N --> A
    N --> B
    N --> C
    N --> D
    
    O --> E
    O --> F
    O --> G
    
    P --> I
    
    Q --> H
    Q --> J
    
    K --> N
    L --> N
    M --> Q
```

## 配置文件扩展图

```mermaid
graph TB
    A[subject_bibliography.yaml] --> B[原有配置]
    A --> C[新增MD处理配置]
    
    C --> D[md_processing]
    D --> E[default_base_path]
    D --> F[recursive_scan]
    D --> G[excel_filename_pattern]
    D --> H[supported_extensions]
    D --> I[title_extraction]
    
    I --> J[remove_extension]
    I --> K[cleanup_rules]
    
    subgraph "配置示例"
        L[default_base_path: data/md_documents]
        M[recursive_scan: true]
        N[excel_filename_pattern: 文章汇总分析_{timestamp}]
        O[supported_extensions: [.md, .markdown]]
    end
    
    E --> L
    F --> M
    G --> N
    H --> O
    J --> P[remove_extension: true]
    K --> Q[cleanup_rules: true]
```

这些流程图清晰地展示了：

1. **整体架构**：新功能如何与现有系统集成
2. **详细流程**：MD文档处理的每个步骤
3. **数据流**：数据在系统中的流转过程
4. **Excel结构**：输出文件的组织方式
5. **配置扩展**：新增的配置项如何组织

这些设计确保了新功能的模块化、可维护性和可扩展性。
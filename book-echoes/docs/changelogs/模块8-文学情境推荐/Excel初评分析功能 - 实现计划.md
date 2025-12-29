# Excel初评分析功能 - 实现计划

## 一、功能概述

为文学推荐系统的Excel导出结果添加LLM初评分析功能，根据候选数量动态选择处理模式：

- **<=10本**: 仅生成推荐语
- **>10本**: 分组筛选模式（每组最多5本，动态计算通过配额，目标最终约10本通过）

---

## 二、需要创建/修改的文件

### 1. 新增文件

| 文件路径                                    | 说明                     |
| ------------------------------------------- | ------------------------ |
| `scripts/excel_initial_review.py`           | 主脚本，包含完整处理逻辑 |
| `prompts/excel_initial_review_filter.md`    | 分组筛选模式提示词       |
| `prompts/excel_initial_review_recommend.md` | 推荐语生成模式提示词     |

### 2. 修改文件

| 文件路径          | 修改内容        |
| ----------------- | --------------- |
| `config/llm.yaml` | 新增2个task配置 |

---

## 三、实现步骤

### 步骤1: 创建提示词文件

#### 文件1: `prompts/excel_initial_review_filter.md`

```markdown
# Role
你是一位资深的文学策展人、阅读推广专家。你的MBTI人格类型是 **INFJ**。你正在为一份高品质书单进行初评筛选。

# Task
你将收到:
1. **用户主题**: 用户最初检索时的自然语言描述
2. **书目列表**: 一组待评估的书籍(每组最多5本)
3. **推荐配额**: 你必须从这个列表中筛选出指定数量的书籍

你的任务:
1. **评估每本书**: 根据用户主题，评估每本书是否符合推荐标准
2. **筛选控制**: 严格遵守推荐配额，选出最优秀的书籍
3. **给出理由**: 为每本通过/未通过的书提供简洁有力的理由

# Evaluation Standards (评估标准)

1. **主题契合度**: 书籍内容是否与用户主题高度相关
2. **阅读价值**: 是否能带来愉悦身心、开阔眼界、激发思维、了解新知的体验
3. **文学品质**: 文字质量、思想深度、叙事技巧
4. **推荐时机**: 是否适合用户当前的情绪状态和阅读场景

# Output Format

请严格遵守以下 JSON 格式，不要包含任何 Markdown 代码块标记，直接输出纯文本 JSON:

{
  "selected_books": [
    {
      "id": "书籍ID",
      "title": "书名",
      "score": 85,
      "reason": "入选理由(2-3句话，直接有力，避免否定句式)"
    }
  ],
  "unselected_books": [
    {
      "id": "书籍ID",
      "title": "书名",
      "reason": "未入选理由(1句话说明)"
    }
  ]
}
```

#### 文件2: `prompts/excel_initial_review_recommend.md`

```markdown
# Role
你是一位资深的文学策展人、阅读推广专家。你的MBTI人格类型是 **INFJ**。你擅长为书籍撰写精准、动人的推荐语。

# Task
你将收到:
1. **用户主题**: 用户最初检索时的自然语言描述
2. **书籍信息**: 单本书的完整元数据

你的任务:
1. **理解主题**: 深入理解用户的阅读期待和情绪需求
2. **提炼价值**: 捕捉这本书最独特的价值点
3. **撰写推荐语**: 用2-3句话写出直击人心的推荐理由

# Writing Style (写作风格)

- **直接有力**: 避免使用"不是...而是..."等否定句式
- **感官化**: 调动通感，用物理质感、空间结构形容阅读体验
- **情境化**: 将书籍置于更广阔的人类经验中
- **精准**: 直击书籍本质，用精准动词作为句子核心

# Output Format

请严格遵守以下 JSON 格式，不要包含任何 Markdown 代码块标记，直接输出纯文本 JSON:

{
  "id": "书籍ID",
  "title": "书名",
  "recommendation": "推荐语内容(2-3句话，直接有力)"
}
```

---

### 步骤2: 修改LLM配置

在 `config/llm.yaml` 末尾（`langfuse:` 配置之前）添加：

```yaml
  # ----------------------------------------------------------------------------
  # 任务: Excel初评-分组筛选模式
  # 逻辑位置: scripts/excel_initial_review.py
  # ----------------------------------------------------------------------------
  excel_initial_review_filter:
    provider_type: text
    temperature: 0.4
    top_p: 0.9
    prompt:
      type: md
      source: "prompts/excel_initial_review_filter.md"

    retry:
      max_retries: 3
      base_delay: 1.0
      max_delay: 10
      enable_provider_switch: true
      jitter: true

    json_repair:
      enabled: true
      strict_mode: false
      output_format: json

    langfuse:
      enabled: true
      name: "Excel初评-分组筛选"
      tags: ["book-echoes", "excel工具", "初评筛选"]
      metadata:
        project: "book-echoes"
        module: "工具脚本"

  # ----------------------------------------------------------------------------
  # 任务: Excel初评-推荐语生成模式
  # 逻辑位置: scripts/excel_initial_review.py
  # ----------------------------------------------------------------------------
  excel_initial_review_recommend:
    provider_type: text-small
    temperature: 0.5
    top_p: 0.9
    prompt:
      type: md
      source: "prompts/excel_initial_review_recommend.md"

    retry:
      max_retries: 3
      base_delay: 1.0
      max_delay: 10
      enable_provider_switch: true
      jitter: true

    json_repair:
      enabled: true
      strict_mode: false
      output_format: json

    langfuse:
      enabled: true
      name: "Excel初评-推荐语生成"
      tags: ["book-echoes", "excel工具", "推荐语"]
      metadata:
        project: "book-echoes"
        module: "工具脚本"
```

---

### 步骤3: 创建主脚本 `scripts/excel_initial_review.py`

**关键类和函数设计**：

```python
# 分组器
class BookGrouper:
    """动态计算分组和通过配额"""
    GROUP_SIZE = 5
    TARGET_FINAL_COUNT = 10

    @staticmethod
    def calculate_group_quota(total_books: int, target_final: int = 10) -> List[Dict]:
        """
        核心算法:
        1. n_groups = ceil(total_books / GROUP_SIZE)
        2. avg_ratio = target_final / total_books
        3. 每组配额 = floor(group_size * avg_ratio)
        4. 最后一组调整确保总数接近target_final
        """

# 处理器
class ExcelReviewProcessor:
    """LLM调用和结果解析"""
    def __init__(self):
        self.llm_client = UnifiedLLMClient()

    def review_group(self, books: List[Dict], theme: str, quota: int) -> Dict:
        """分组筛选: 调用 excel_initial_review_filter 任务"""

    def generate_recommendation(self, book: Dict, theme: str) -> Dict:
        """推荐语生成: 调用 excel_initial_review_recommend 任务"""

# 主脚本
class ExcelInitialReviewScript:
    """Excel初评分析主脚本"""

    def _read_excel(self) -> Tuple[pd.DataFrame, str]:
        """读取推荐结果sheet + 提取元信息中的主题"""

    def _determine_mode(self, df: pd.DataFrame) -> str:
        """<=10本返回recommend_only，>10本返回filter"""

    def _execute_filter_mode(self, df: pd.DataFrame, theme: str) -> pd.DataFrame:
        """分组筛选模式: 计算分组 -> 逐组调用LLM -> 写入结果"""

    def _execute_recommend_only_mode(self, df: pd.DataFrame, theme: str) -> pd.DataFrame:
        """推荐语模式: 逐本书调用LLM -> 写入推荐语"""

    def _save_excel(self, df: pd.DataFrame) -> str:
        """保存文件(添加_初评_时间戳后缀)"""

# 命令行入口
def main():
    """支持 --excel 参数和交互式输入"""
```

**Excel新增列**:

- `初评结果`: 通过/未通过
- `初评分数`: 0-100
- `初评理由`: LLM生成的推荐理由
- `人工评选`: 空列
- `人工推荐语`: 空列

---

### 步骤4: 核心算法详解

#### 分组配额计算示例

| 候选数 | 分组             | 每组配额         | 通过总数 |
| ------ | ---------------- | ---------------- | -------- |
| 11本   | 3组(4,4,3)       | 4, 3, 3          | 10本     |
| 15本   | 3组(5,5,5)       | 3, 3, 4          | 10本     |
| 20本   | 4组(5,5,5,5)     | 2, 2, 3, 3       | 10本     |
| 30本   | 6组(5,5,5,5,5,5) | 2, 2, 2, 2, 2, 2 | 12本*    |
| 50本   | 10组             | 1, 1, ...        | 10本     |

*注: 30本会略超过10本，这是可接受的

---

## 四、使用方式

```bash
# 方式1: 交互式输入
python scripts/excel_initial_review.py

# 方式2: 指定文件
python scripts/excel_initial_review.py --excel "path/to/推荐结果.xlsx"

# 方式3: 试运行(不保存)
python scripts/excel_initial_review.py --excel "path/to/推荐结果.xlsx" --dry-run
```

---

## 五、关键依赖

### 内部模块

- `src.utils.llm.client.UnifiedLLMClient` - LLM调用
- `src.utils.logger.get_logger` - 日志

### 外部包(已安装)

- `pandas` - DataFrame操作
- `openpyxl` - Excel读写
- `yaml` - 配置解析

---

## 六、注意事项

1. **书目ID匹配**: 使用Excel中的`条码`列(bookmark)作为唯一标识
2. **元数据字段**: 从`douban_rating`, `douban_title`, `douban_subtitle`, `douban_author`, `douban_summary`, `douban_author_intro`, `douban_catalog`列获取
3. **主题提取**: 从`元信息`sheet的`主题`行的`内容`列获取
4. **错误处理**: LLM调用失败时标记"ERROR: [原因]"，不中断整体流程
5. **进度显示**: 每组/每本书显示处理进度，组间延迟2秒避免API限流
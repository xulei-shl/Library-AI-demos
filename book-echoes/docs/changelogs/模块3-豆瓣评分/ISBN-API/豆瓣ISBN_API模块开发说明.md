# 豆瓣 ISBN API 模块开发说明

## 需求概述

在现有模块3（豆瓣模块）的基础上，新增一个独立的流程逻辑：

**原流程（保留不变）**：FOLIO ISBN 获取 → 豆瓣链接解析 → 评分过滤 → 豆瓣 Subject API

**新流程**：FOLIO ISBN 获取 → 豆瓣 ISBN API → 评分过滤

### 核心差异

| 对比项 | 原流程 | 新流程 |
|--------|--------|--------|
| 链接获取方式 | 通过爬虫搜索豆瓣获取图书链接 | 直接使用 ISBN 调用 API |
| API 端点 | `https://m.douban.com/rexxar/api/v2/subject/{subject_id}` | `https://m.douban.com/rexxar/api/v2/book/isbn/{isbn}` |
| 速度 | 较慢（需要浏览器爬取） | 较快（直接 API 调用） |
| 适用场景 | ISBN 缺失或需要精确匹配时 | ISBN 数据质量较高时 |

---

## 技术方案

### 1. 文件结构

在 `src/core/douban/` 目录下新建以下文件：

```
src/core/douban/
├── api/
│   ├── isbn_client.py          # 新增：ISBN API 客户端
│   └── subject_client.py       # 现有：Subject API 客户端（保持不变）
├── pipelines/
│   ├── douban_isbn_api_pipeline.py  # 新增：ISBN API 流水线
│   └── ...                          # 现有文件（保持不变）
└── douban_isbn_main.py         # 新增：ISBN API 模块主程序入口
```

### 2. 核心组件设计

#### 2.1 ISBN API 客户端 (`api/isbn_client.py`)

**职责**：封装豆瓣 ISBN API 的调用逻辑

**API 接口**：
- 地址：`https://m.douban.com/rexxar/api/v2/book/isbn/{isbn}`
- 方法：GET
- 参数：ISBN（去掉 `-` 分隔符的纯数字）

**设计要点**：
```python
class IsbnApiClient:
    """豆瓣 ISBN API 客户端"""

    def __init__(
        self,
        timeout: float = 10.0,
        max_concurrent: int = 3,      # 并发数
        qps: float = 1.0,             # 每秒请求数（建议保守值）
        retry: Optional[Dict] = None,
        headers: Optional[Dict] = None,
    ):
        # 复用现有 rate_limiter.py 的 AsyncRateLimiter
        pass

    async def fetch_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """根据ISBN获取图书信息"""
        pass

    async def fetch_batch(self, isbn_list: Iterable[str]) -> Dict[str, Optional[Dict]]:
        """批量获取"""
        pass
```

**反爬策略**（重点）：

```python
# 1. 随机延迟（在 rate_limiter 基础上增加随机性）
import random

async def _random_delay(self):
    """随机延迟 1.5-3.5 秒"""
    delay = random.uniform(1.5, 3.5)
    await asyncio.sleep(delay)

# 2. 请求头模拟
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                  "Version/14.0 Mobile/15E148 Safari/604.1",
    "Referer": "https://m.douban.com/",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# 3. User-Agent 池轮换
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0...",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0...",
    "Mozilla/5.0 (Linux; Android 10...",
    # 更多移动端 UA
]

# 4. 失败退避策略
RETRY_CONFIG = {
    "max_times": 3,
    "backoff": [2, 5, 10],  # 指数退避
}

# 5. 批次间长间隔
async def _batch_cooldown(self, batch_index: int):
    """每处理 N 条后休息较长时间"""
    if batch_index > 0 and batch_index % 20 == 0:
        cooldown = random.uniform(30, 60)
        logger.info(f"批次冷却：休息 {cooldown:.1f} 秒...")
        await asyncio.sleep(cooldown)
```

#### 2.2 ISBN API 流水线 (`pipelines/douban_isbn_api_pipeline.py`)

**职责**：编排完整的 ISBN API 处理流程

**流程步骤**：

```
┌─────────────────────────────────────────────────────────────┐
│                    ISBN API 流水线                           │
├─────────────────────────────────────────────────────────────┤
│  1. 数据加载                                                 │
│     └─ 读取 Excel，获取 ISBN 列                              │
│                                                             │
│  2. ISBN 预处理                                              │
│     ├─ 去除分隔符 (978-7-5057-1566-0 → 9787505715660)       │
│     ├─ 校验格式（10位或13位数字）                            │
│     └─ 过滤无效 ISBN                                        │
│                                                             │
│  3. 数据库查重（可选，复用现有逻辑）                          │
│     └─ 检查 books_history.db 是否已有数据                   │
│                                                             │
│  4. ISBN API 调用                                            │
│     ├─ 批量异步请求（带反爬策略）                            │
│     ├─ 数据映射（复用 subject_mapper.py）                   │
│     └─ 实时写入 Excel                                       │
│                                                             │
│  5. 评分过滤（复用现有 DynamicThresholdFilter）              │
│     └─ 根据主题分类动态筛选候选图书                          │
│                                                             │
│  6. 结果输出                                                 │
│     ├─ 生成最终 Excel                                       │
│     └─ 生成处理报告                                         │
└─────────────────────────────────────────────────────────────┘
```

**代码结构**：

```python
@dataclass
class DoubanIsbnApiPipelineOptions:
    """ISBN API 流水线配置"""
    excel_file: str
    barcode_column: str = "书目条码"
    isbn_column: str = "ISBN"
    # 反爬配置
    max_concurrent: int = 2
    qps: float = 0.5                    # 每秒 0.5 次请求（即每 2 秒 1 次）
    random_delay_min: float = 1.5
    random_delay_max: float = 3.5
    batch_cooldown_interval: int = 20   # 每 20 条休息一次
    batch_cooldown_min: float = 30.0
    batch_cooldown_max: float = 60.0
    # 数据库配置
    disable_database: bool = False
    force_update: bool = False
    # 保存配置
    save_interval: int = 10
    generate_report: bool = True


class DoubanIsbnApiPipeline:
    """豆瓣 ISBN API 流水线"""

    def run(self, options: DoubanIsbnApiPipelineOptions) -> Tuple[str, Dict]:
        # 实现流水线逻辑
        pass
```

#### 2.3 主程序入口 (`douban_isbn_main.py`)

**职责**：提供命令行入口，供 `main.py` 调用

```python
def main():
    parser = argparse.ArgumentParser(description='豆瓣ISBN API模块')
    parser.add_argument('command', choices=['run', 'help'])
    parser.add_argument('--excel-file', required=True)
    parser.add_argument('--isbn-column', default='ISBN')
    # 反爬参数
    parser.add_argument('--max-concurrent', type=int, default=2)
    parser.add_argument('--qps', type=float, default=0.5)
    # ...
```

### 3. 主流程集成 (`main.py`)

修改主菜单，新增选项：

```python
def main():
    while True:
        print("\n请选择要运行的功能模块:")
        print("1. 模块1/2: 月归还数据分析 + 智能筛选")
        print("2. 模块3: 豆瓣模块（FOLIO ISBN + 豆瓣链接 + 评分过滤 + 豆瓣 API）")
        print("3. 模块3-B: 豆瓣模块（FOLIO ISBN + 豆瓣 ISBN API + 评分过滤）")  # 新增
        print("4. 数据采集流程: 模块1 -> 模块2 -> 模块3")
        print("5. 模块4: 初评（海选阶段）")
        print("6. 模块4: 完整评选（初评→决选→终评）")
        print("7. 数据分析与评选流程: 模块1 -> 模块2 -> 模块3 -> 模块4")
        print("8. 模块5: 图书卡片生成（含借书卡）")
        print("9. 模块6: 新书零借阅（睡美人）筛选")
        print("10. 模块7: 主题书目每日追踪")
        print("11. 退出程序")
```

新增运行函数：

```python
def run_module3b():
    """运行模块3-B：豆瓣ISBN API模块"""
    print("=" * 60)
    print("模块3-B: 豆瓣ISBN API模块")
    print("FOLIO ISBN获取 + 豆瓣ISBN API + 评分过滤")
    print("=" * 60)

    # 1. 查找输入文件
    target_excel = find_latest_screening_result_excel()
    if not target_excel:
        print("错误: 未找到筛选结果 Excel 文件。")
        return 1

    # 2. 调用新模块
    isbn_api_script = Path(__file__).parent / "src" / "core" / "douban" / "douban_isbn_main.py"
    cmd = [sys.executable, str(isbn_api_script), "run", "--excel-file", str(target_excel)]
    result = subprocess.run(cmd, capture_output=False)

    return 0 if result.returncode == 0 else 1
```

---

## 配置设计

### 新增配置项 (`config/setting.yaml`)

```yaml
douban:
  # ... 现有配置保持不变 ...

  # 新增：ISBN API 配置
  isbn_api:
    enabled: true
    base_url: "https://m.douban.com/rexxar/api/v2/book/isbn"

    # 并发与限流（保守配置，避免触发反爬）
    max_concurrent: 2      # 最大并发数
    qps: 0.5              # 每秒请求数（0.5 = 每 2 秒 1 次）
    timeout: 15           # 请求超时（秒）

    # 随机延迟配置
    random_delay:
      enabled: true
      min: 1.5            # 最小延迟（秒）
      max: 3.5            # 最大延迟（秒）

    # 批次冷却配置
    batch_cooldown:
      enabled: true
      interval: 20        # 每处理 N 条触发冷却
      min: 30             # 冷却最小时间（秒）
      max: 60             # 冷却最大时间（秒）

    # 重试配置
    retry:
      max_times: 3
      backoff: [2, 5, 10]

    # User-Agent 池
    user_agents:
      - "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
      - "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"
      - "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36"
      - "Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36"
```

---

## 数据映射

ISBN API 返回的 JSON 结构与 Subject API 相同，可复用现有的 `subject_mapper.py`：

```python
# api/subject_mapper.py（已存在，无需修改）
def map_subject_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """将 subject API 数据映射成统一逻辑字段"""
    # 返回格式：
    # {
    #     "rating": 8.5,
    #     "rating_count": 1234,
    #     "title": "书名",
    #     "author": "作者",
    #     "publisher": "出版社",
    #     "summary": "简介",
    #     "cover_image": "封面URL",
    #     ...
    # }
```

写入 Excel 时复用 `fields_mapping.douban` 配置。

---

## 错误处理

### API 响应状态码处理

| 状态码 | 含义 | 处理方式 |
|--------|------|----------|
| 200 | 成功 | 解析数据 |
| 404 | ISBN 不存在 | 记录为"未找到"，继续处理 |
| 429 | 请求过快 | 等待退避时间后重试 |
| 500/502/503 | 服务器错误 | 等待退避时间后重试 |

### 常见错误场景

1. **ISBN 格式错误**：跳过并记录
2. **网络超时**：重试 3 次
3. **反爬触发**：长时间冷却后重试
4. **数据解析失败**：记录错误，继续处理下一条

---

## 实现步骤

### 阶段一：基础框架

1. 创建 `api/isbn_client.py`
   - 实现 `IsbnApiClient` 类
   - 集成 `AsyncRateLimiter`
   - 添加随机延迟和 UA 轮换

2. 创建 `pipelines/douban_isbn_api_pipeline.py`
   - 实现 `DoubanIsbnApiPipelineOptions`
   - 实现 `DoubanIsbnApiPipeline`
   - 集成 ISBN 预处理逻辑

### 阶段二：流程集成

3. 创建 `douban_isbn_main.py`
   - 实现命令行接口
   - 添加参数解析

4. 修改 `main.py`
   - 添加菜单选项
   - 实现 `run_module3b()`

### 阶段三：评分过滤

5. 集成评分过滤
   - 复用 `DynamicThresholdFilter`
   - 复用 `ProgressManager`

### 阶段四：测试与优化

6. 编写测试用例
7. 调优反爬参数
8. 编写用户文档

---

## 复用清单

以下现有组件可直接复用：

| 组件 | 文件路径 | 用途 |
|------|----------|------|
| 限流器 | `api/rate_limiter.py` | 控制 QPS 和并发 |
| 数据映射 | `api/subject_mapper.py` | JSON → Dict 转换 |
| 进度管理 | `progress_manager.py` | 进度保存和恢复 |
| 动态过滤 | `analytics/dynamic_threshold_filter.py` | 评分筛选 |
| 数据库管理 | `database/database_manager.py` | 历史数据查重 |
| 报告生成 | `report_generator.py` | 处理报告 |
| 配置管理 | `src/utils/config_manager.py` | 读取配置 |
| 日志工具 | `src/utils/logger.py` | 日志记录 |

---

## 注意事项

1. **反爬是核心**：豆瓣对 API 有较严格的反爬措施，必须：
   - 使用较低的 QPS（建议 0.5 以下）
   - 添加随机延迟
   - 定期长间隔休息
   - 使用移动端 UA

2. **保留原流程**：新流程是补充而非替代，原流程在 ISBN 缺失时仍有价值

3. **增量处理**：利用数据库查重避免重复请求

4. **失败降级**：ISBN API 失败的记录可手动标记，后续使用原流程补充

---

## 参考资料

- 现有 Subject API 实现：[subject_client.py](../../../src/core/douban/api/subject_client.py)
- 限流器实现：[rate_limiter.py](../../../src/core/douban/api/rate_limiter.py)
- 数据映射：[subject_mapper.py](../../../src/core/douban/api/subject_mapper.py)
- 动态过滤：[dynamic_threshold_filter.py](../../../src/core/douban/analytics/dynamic_threshold_filter.py)

---

完成总结
我已根据开发文档实现了新的豆瓣 ISBN API 流程。以下是创建和修改的文件：
新创建的文件
api/isbn_client.py - ISBN API 客户端
IsbnApiClient 类：封装豆瓣 ISBN API 调用
反爬策略：随机延迟、User-Agent 轮换、批次冷却、指数退避重试
normalize_isbn() 函数：标准化 ISBN（去除分隔符）
支持单条和批量获取
pipelines/douban_isbn_api_pipeline.py - ISBN API 流水线
DoubanIsbnApiPipeline 类：完整的处理流水线
流程步骤：数据加载 → ISBN预处理 → 数据库查重 → ISBN API调用 → 数据映射 → 评分过滤 → 结果输出
复用现有组件：ProgressManager、DatabaseManager、DynamicThresholdFilter、subject_mapper
douban_isbn_main.py - 主程序入口
命令行接口：run 和 help 命令
支持所有配置参数的命令行覆盖
修改的文件
config/setting.yaml - 新增 isbn_api 配置节
并发与限流配置
随机延迟配置
批次冷却配置
重试配置
User-Agent 池
main.py - 添加模块3-B菜单选项
新增 run_module3b() 函数
菜单选项从10个增加到11个
pipelines/init.py - 导出新流水线
api/init.py - 导出新客户端
原有流程完全保留
所有原有的豆瓣模块代码（爬虫搜索、链接解析、Subject API 等）均未修改，保持原样。新流程作为独立的模块3-B存在。
使用方式
# 通过主菜单运行（选择选项3）
python main.py

# 或直接运行 ISBN API 模块
python src/core/douban/douban_isbn_main.py run  --excel-file "E:\Desk\1.xlsx" --disable-database

# 查看帮助
python src/core/douban/douban_isbn_main.py help

---

P1: 代码重构 - 拆分大文件
原文件行数: 1063 行 → 精简后: 320 行 新建模块目录: src/core/douban/pipelines/isbn_api_steps/

文件	行数	职责
constants.py	15	状态常量 ProcessStatus
isbn_preprocessor.py	230	ISBN 预处理和补充检索
database_checker.py	200	数据库查重和填充
api_caller.py	220	ISBN API 调用
rating_filter.py	75	评分过滤
database_writer.py	115	数据库写入
report_generator.py	155	输出结果和报告生成

P2: 状态常量提取
状态常量已提取到 ProcessStatus 类中（constants.py），各模块统一引用。
重要说明
数据库写入逻辑未变: 所有 STATUS_DONE 的记录都会写入数据库，与评分过滤无关
向后兼容: 主流水线 API 保持不变，DoubanIsbnApiPipelineOptions 接口一致
所有语法已验证通过
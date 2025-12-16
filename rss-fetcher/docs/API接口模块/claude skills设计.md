# Local Book Researcher - Claude Skill 设计文档

## 概述

Local Book Researcher 是一个 Claude Code Skill，用于与本地图书检索API交互，提供简单检索和深度研究两种模式。

## 1. 标准化目录结构

```text
local-book-researcher/
├── skill.json                    # 技能配置文件（必需）
├── Skill.md                      # 技能说明文档（必需）
├── README.md                     # 安装和使用说明
├── requirements.txt              # Python依赖列表
├── .gitignore                    # Git忽略文件
├── tools/                        # 工具脚本目录
│   └── book_api_client.py        # 增强的API客户端
└── prompts/                      # 提示词文件目录
    ├── search/                   # 搜索相关提示词
    │   └── simple_search.md
    ├── analysis/                 # 分析相关提示词
    │   ├── article_analysis.md
    │   └── cross_analysis.md
    └── recommendation/           # 推荐相关提示词
        └── intro.md
```

## 2. 技能配置文件：skill.json

```json
{
  "name": "local-book-researcher",
  "version": "1.0.0",
  "description": "本地智能图书检索专家，支持简单检索和深度研究模式",
  "author": "Library AI Team",
  "license": "MIT",
  "main": "Skill.md",
  "dependencies": [
    "python>=3.8",
    "requests>=2.25.0"
  ],
  "keywords": ["books", "research", "library", "local-search"],
  "repository": {
    "type": "git",
    "url": "https://github.com/your-org/Library-AI-demos"
  },
  "environment": {
    "BOOK_API_URL": "http://localhost:8000",
    "BOOK_API_TIMEOUT": "30"
  }
}
```

## 3. 核心技能文档：Skill.md

---
name: Local Book Researcher
version: 1.0.0
description: 本地智能图书检索专家，支持简单检索和深度研究模式
dependencies: python>=3.8, requests
---

# 本地图书检索助手

我是一个专门帮助您检索本地图书资源的智能助手。我可以提供两种检索模式：

## 🔍 简单检索模式
适用于：
- 查找特定书籍
- 搜索特定作者的作品
- 基于关键词的快速查询

**使用示例**：
- "帮我查找《三体》这本书"
- "搜索刘慈欣的科幻小说"
- "有什么关于人工智能的入门书籍？"

## 📚 深度研究模式
适用于：
- 跨学科主题探索
- 需要背景资料的研究性查询
- 综合性图书推荐

**使用示例**：
- "帮我深入研究量子计算在密码学中的应用"
- "深度搜索关于宋朝历史的最新研究资料"
- "探索可持续发展和城市规划的相关书籍"

## 💡 使用提示
- 简单问题我会直接使用快速检索
- 复杂问题我会通过外部调研→分析→检索的流程为您提供深度答案
- 所有查询都基于您的本地图书数据库

## 4. 增强的API客户端：tools/book_api_client.py

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced API client for Local Book Researcher Claude Skill.
Provides robust communication with the local book retrieval API.
"""

import os
import sys
import json
import logging
import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BookAPIClient:
    """增强的图书API客户端，支持重试、超时和错误处理"""

    def __init__(self, base_url: Optional[str] = None):
        """初始化API客户端

        Args:
            base_url: API基础URL，默认从环境变量获取
        """
        self.base_url = base_url or os.getenv('BOOK_API_URL', 'http://localhost:8000')
        self.timeout = int(os.getenv('BOOK_API_TIMEOUT', '30'))

        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"初始化API客户端，目标URL: {self.base_url}")

    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """发送HTTP请求并处理响应

        Args:
            endpoint: API端点路径
            payload: 请求载荷

        Returns:
            API响应数据

        Raises:
            requests.RequestException: 请求失败
        """
        url = f"{self.base_url}/api/books/{endpoint}"

        try:
            logger.info(f"发送请求到: {url}")
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"请求超时: {url}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"连接失败: {url}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP错误 {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            raise

    def simple_search(self, query: str, **kwargs) -> str:
        """执行简单检索并返回纯文本结果

        Args:
            query: 查询文本
            **kwargs: 其他可选参数（top_k, min_rating等）

        Returns:
            格式化的纯文本结果
        """
        payload = {
            "query": query,
            "response_format": "plain_text",
            **kwargs
        }

        try:
            data = self._make_request("text-search", payload)
            return data.get("context_plain_text", "未找到相关书籍。")
        except Exception as e:
            logger.error(f"简单检索失败: {str(e)}")
            return f"检索失败: {str(e)}"

    def deep_search(self, markdown_text: str, **kwargs) -> str:
        """执行深度检索并返回纯文本结果

        Args:
            markdown_text: Markdown格式的检索描述
            **kwargs: 其他可选参数（per_query_top_k, final_top_k等）

        Returns:
            格式化的纯文本结果
        """
        payload = {
            "markdown_text": markdown_text,
            "response_format": "plain_text",
            "enable_rerank": True,  # 深度检索默认启用重排序
            **kwargs
        }

        try:
            data = self._make_request("multi-query", payload)
            return data.get("context_plain_text", "未找到相关书籍。")
        except Exception as e:
            logger.error(f"深度检索失败: {str(e)}")
            return f"检索失败: {str(e)}"

def main():
    """命令行入口点"""
    if len(sys.argv) < 3:
        print("用法: python book_api_client.py <simple|deep> '<查询文本>'")
        sys.exit(1)

    client = BookAPIClient()
    mode = sys.argv[1].lower()
    text = sys.argv[2]

    if mode == "simple":
        print(client.simple_search(text))
    elif mode == "deep":
        print(client.deep_search(text))
    else:
        print(f"错误: 未知模式 '{mode}'，请使用 'simple' 或 'deep'")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## 5. 提示词文件组织

### 5.1 搜索提示词：prompts/search/simple_search.md
```markdown
# 简单图书检索提示词

你是一个图书检索助手。根据用户提供的查询内容和API返回的图书列表，生成简洁、有用的回答。

回答格式要求：
1. 直接相关的书籍优先列出
2. 每本书包含：书名、作者、评分、简介
3. 如果没有完全匹配的结果，提供相似推荐
4. 保持回答简洁明了
```

### 5.2 分析提示词：prompts/analysis/article_analysis.md
```markdown
# 单篇文章分析提示词

请分析以下文章，提取与图书检索相关的关键信息：

分析要点：
1. 核心观点和主题
2. 提及的具体书籍（书名、作者）
3. 相关研究领域或关键词
4. 潜在的检索方向

输出格式：
- 核心主题：
- 推荐书籍：
- 研究关键词：
- 延伸方向：
```

### 5.3 交叉分析提示词：prompts/analysis/cross_analysis.md
```markdown
# 多篇文章交叉分析提示词

基于多篇分析文章，整合生成图书检索策略。

任务要求：
1. 识别3-5个核心检索维度
2. 提取高频关键词
3. 构建检索主题的背景上下文
4. 生成结构化的Markdown检索草案

输出格式：
# 检索主题：[主题名称]

## 核心关键词
- 关键词1
- 关键词2
- 关键词3

## 背景上下文
[简要描述检索目标和范围]
```

### 5.4 推荐提示词：prompts/recommendation/intro.md
```markdown
# 图书推荐导语生成提示词

作为资深书评人，基于以下检索结果和前期调研，生成引人入胜的推荐导语。

导语要求：
1. 回应用户最初的问题
2. 突出推荐书籍的价值
3. 说明为什么这些书适合用户
4. 语言简洁有力，富有吸引力
```

## 6. 必要的支持文件

### 6.1 requirements.txt
```
requests>=2.25.0
urllib3>=1.26.0
```

### 6.2 .gitignore
```
__pycache__/
*.pyc
.env
.DS_Store
*.log
```

### 6.3 README.md
```markdown
# Local Book Researcher Claude Skill

## 安装说明

1. 确保Python 3.8+环境
2. 安装依赖：`pip install -r requirements.txt`
3. 启动本地API服务（默认运行在 http://localhost:8000）
4. 在Claude Code中加载此Skill

## 环境变量配置

```bash
export BOOK_API_URL=http://localhost:8000
export BOOK_API_TIMEOUT=30
```

## 使用方式

- 简单检索：直接询问特定书籍或作者
- 深度研究：使用"深入研究"、"探索"等关键词

## 故障排除

1. 确保API服务正在运行
2. 检查网络连接
3. 查看日志了解详细错误信息
```

## 7. 方案优势

1. **标准化架构**：完全符合Claude Skills官方规范
2. **模块化设计**：清晰的目录结构和职责分离
3. **健壮性**：完善的错误处理和重试机制
4. **可配置性**：通过环境变量灵活配置
5. **可维护性**：详细的日志和文档支持
6. **扩展性**：易于添加新功能和提示词模板
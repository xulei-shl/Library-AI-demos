"""
Reranker重排序器（API模式）
使用重排序模型对Top结果进行精细打分
"""

import json
import os
import time
from typing import Dict, List

import httpx
from openai import OpenAI

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """
    API重排序器

    通过API调用重排序模型对query-doc对进行精细打分
    使用 Qwen/Qwen3-Reranker-8B 模型
    """

    def __init__(self, config: Dict):
        """
        初始化重排序器

        Args:
            config: 配置字典，包含：
                - model: 模型名称
                - api_key: API密钥
                - base_url: API基础URL
                - max_retries: 最大重试次数
                - timeout: 超时时间
                - retry_delay: 重试延迟
        """
        self.config = config
        self.client = self._init_client()
        self._initialized = True

    def _init_client(self) -> OpenAI:
        """初始化OpenAI客户端"""
        api_key = self._resolve_env(self.config['api_key'])
        http_client = httpx.Client(
            timeout=self.config['timeout'],
            trust_env=False
        )
        return OpenAI(
            api_key=api_key,
            base_url=self.config['base_url'],
            http_client=http_client
        )

    def _resolve_env(self, value: str) -> str:
        """解析环境变量"""
        if value.startswith('env:'):
            return os.getenv(value[4:], '')
        return value

    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 30,
        batch_size: int = 32
    ) -> List[Dict]:
        """
        重排序

        Args:
            query: 原始查询文本
            results: 待重排序的结果列表
            top_k: 返回TopK
            batch_size: 批处理大小

        Returns:
            重排序后的结果列表，包含 rerank_score 字段
        """
        try:
            if not results:
                return results

            logger.info(f"开始重排序: 输入={len(results)}条, top_k={top_k}")

            # 构建文档列表
            docs = [self._build_doc_text(r) for r in results]

            # 调用Reranker API
            scores = self._call_reranker_api(query, docs, batch_size)

            # 添加分数并排序
            for r, score in zip(results, scores):
                r["rerank_score"] = round(float(score), 4)

            # 按rerank_score排序
            sorted_results = sorted(
                results,
                key=lambda x: x["rerank_score"],
                reverse=True
            )

            final_results = sorted_results[:top_k]

            logger.info(
                f"重排序完成: 输出={len(final_results)}条, "
                f"最高分={final_results[0]['rerank_score']:.4f}"
            )

            return final_results

        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            # 降级：返回原始结果（按原排序字段）
            return results[:top_k]

    def _call_reranker_api(
        self,
        query: str,
        docs: List[str],
        batch_size: int
    ) -> List[float]:
        """
        调用Reranker API

        Args:
            query: 查询文本
            docs: 文档列表
            batch_size: 批处理大小

        Returns:
            分数列表
        """
        all_scores = []

        # 分批处理
        for i in range(0, len(docs), batch_size):
            batch_docs = docs[i:i + batch_size]

            # 重试机制
            for attempt in range(self.config['max_retries']):
                try:
                    response = self.client.beta.chat.completions.parse(
                        model=self.config['model'],
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个文档重排序助手。"
                            },
                            {
                                "role": "user",
                                "content": self._build_prompt(query, batch_docs)
                            }
                        ],
                        # 使用结构化输出
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": "rerank_scores",
                                "strict": True,
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "scores": {
                                            "type": "array",
                                            "items": {"type": "number"}
                                        }
                                    },
                                    "required": ["scores"]
                                }
                            }
                        }
                    )

                    # 解析响应
                    result = json.loads(response.choices[0].message.content)
                    scores = result.get('scores', [])
                    all_scores.extend(scores)
                    break

                except Exception as e:
                    if attempt < self.config['max_retries'] - 1:
                        logger.warning(f"Reranker API 调用失败，重试 {attempt + 1}/{self.config['max_retries']}: {e}")
                        time.sleep(self.config['retry_delay'])
                    else:
                        logger.error(f"Reranker API 调用失败: {e}")
                        # 返回均匀分数作为降级
                        all_scores.extend([0.5] * len(batch_docs))

        return all_scores

    def _build_prompt(self, query: str, docs: List[str]) -> str:
        """
        构建提示词

        Args:
            query: 查询文本
            docs: 文档列表

        Returns:
            提示词
        """
        prompt = f"""请根据查询内容，对以下文档进行相关性打分（0-1之间的小数）。

查询：{query}

文档列表：
"""
        for i, doc in enumerate(docs):
            # 截断过长的文档
            doc_preview = doc[:500] if len(doc) > 500 else doc
            prompt += f"\n{i+1}. {doc_preview}"

        prompt += """

请返回JSON格式，包含一个scores数组，按顺序给出每个文档的相关性分数：
{"scores": [0.85, 0.72, 0.93, ...]}"""
        return prompt

    def _build_doc_text(self, result: Dict) -> str:
        """
        构建文档文本（用于重排序）

        Args:
            result: 单个检索结果

        Returns:
            文档文本
        """
        parts = []

        # 书名（高权重）
        title = result.get("title", "")
        if title:
            parts.extend([title] * 2)

        # 作者
        author = result.get("author", "")
        if author:
            parts.append(author)

        # 从tags_json提取更多信息
        tags_json = result.get("tags_json", "")
        if tags_json:
            try:
                tags = json.loads(tags_json)
                # LLM推理（最高权重）
                reasoning = tags.get("reasoning", "")
                if reasoning:
                    parts.extend([reasoning] * 2)
                # 简介
                summary = tags.get("douban_summary", "")
                if summary:
                    parts.append(summary[:500])
            except json.JSONDecodeError:
                pass

        return " ".join(parts) if parts else "这是一本书"

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def unload(self):
        """释放资源"""
        if self.client is not None:
            self.client.close()
            self._initialized = False
            logger.info("Reranker客户端已关闭")

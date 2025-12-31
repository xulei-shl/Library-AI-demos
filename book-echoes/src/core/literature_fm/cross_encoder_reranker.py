"""
CrossEncoder重排序器
使用重排序模型对Top结果进行精细打分
"""

import json
from typing import Dict, List

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CrossEncoderReranker:
    """
    CrossEncoder重排序器

    使用交叉编码器模型对query-doc对进行精细打分
    相比于双塔模型（如Embedding），CrossEncoder会同时考虑query和doc的交互，
    通常能获得更好的排序效果，但计算成本更高

    常用模型：
    - BAAI/bge-reranker-v2-m3: 多语言重排序模型，支持中文
    - BAAI/bge-reranker-large: 英文大模型
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu"
    ):
        """
        初始化重排序器

        Args:
            model_name: 模型名称或路径
            device: 运行设备 ("cpu" 或 "cuda")
        """
        self.model_name = model_name
        self.device = device
        self.model = None
        self._initialized = False

    def _lazy_init(self):
        """延迟初始化模型（首次调用时加载）"""
        if self._initialized:
            return

        try:
            from sentence_transformers import CrossEncoder
            import torch

            # 检查CUDA可用性
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA不可用，使用CPU")
                self.device = "cpu"

            logger.info(f"加载CrossEncoder模型: {self.model_name} (device={self.device})")
            self.model = CrossEncoder(
                model_name=self.model_name,
                device=self.device
            )
            self._initialized = True
            logger.info("✓ CrossEncoder模型加载完成")

        except ImportError as e:
            logger.error(f"缺少依赖: {e}，请安装 sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"CrossEncoder模型加载失败: {str(e)}")
            raise

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

            # 延迟初始化
            self._lazy_init()

            logger.info(f"开始重排序: 输入={len(results)}条, top_k={top_k}")

            # 构建query-doc对
            pairs = []
            for r in results:
                doc_text = self._build_doc_text(r)
                pairs.append([query, doc_text])

            # 批量打分
            scores = self.model.predict(pairs, batch_size=batch_size)

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

    def _build_doc_text(self, result: Dict) -> str:
        """
        构建文档文本（用于重排序）

        Args:
            result: 单个检索结果

        Returns:
            str: 文档文本
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
        """检查模型是否已初始化"""
        return self._initialized

    def unload(self):
        """卸载模型（释放内存）"""
        if self.model is not None:
            del self.model
            self.model = None
            self._initialized = False
            logger.info("CrossEncoder模型已卸载")

"""
RRF融合器
使用 Reciprocal Rank Fusion 算法合并多路检索结果
"""

from typing import Dict, List

from src.utils.logger import get_logger

logger = get_logger(__name__)


class RRFFusion:
    """
    Reciprocal Rank Fusion 融合器

    RRF算法原理：
    score(book_id) = Σ(1 / (k + rank_i))

    其中：
    - rank_i: 该书在第i路结果中的排名（从1开始）
    - k: 平滑常数，通常取60
    - 如果某本书未在某路结果中出现，则rank_i = ∞，贡献为0

    RRF的优势：
    1. 不需要归一化分数（不同检索器的分数尺度不同）
    2. 对排名敏感而非分数值，更稳健
    3. 简单高效，易于实现
    """

    def __init__(self, k: int = 60):
        """
        初始化RRF融合器

        Args:
            k: RRF平滑常数，默认60
               - 较小的k（如30）：更关注排名靠前的结果
               - 较大的k（如100）：更平均地考虑所有结果
        """
        self.k = k

    def merge(
        self,
        results_a: List[Dict],
        results_b: List[Dict],
        rank_key_a: str = "vector_score",
        rank_key_b: str = "bm25_score"
    ) -> List[Dict]:
        """
        融合两路检索结果

        Args:
            results_a: 第一路结果（如向量检索）
            results_b: 第二路结果（如BM25检索）
            rank_key_a: 第一路结果的排序字段
            rank_key_b: 第二路结果的排序字段

        Returns:
            融合后的结果列表，包含 rrf_score 和 sources 字段
        """
        try:
            # 构建排名映射
            scores = {}

            # 处理第一路结果
            for rank, item in enumerate(results_a, start=1):
                book_id = item.get("book_id")
                if not book_id:
                    continue

                if book_id not in scores:
                    scores[book_id] = {
                        "data": item,
                        "rrf_score": 0,
                        "sources": [],
                        "vector_rank": rank,
                        "bm25_rank": None
                    }

                # RRF贡献分数
                scores[book_id]["rrf_score"] += 1 / (self.k + rank)
                scores[book_id]["sources"].append("vector")

            # 处理第二路结果
            for rank, item in enumerate(results_b, start=1):
                book_id = item.get("book_id")
                if not book_id:
                    continue

                if book_id not in scores:
                    scores[book_id] = {
                        "data": item,
                        "rrf_score": 0,
                        "sources": [],
                        "vector_rank": None,
                        "bm25_rank": rank
                    }

                # RRF贡献分数
                scores[book_id]["rrf_score"] += 1 / (self.k + rank)
                if "bm25" not in scores[book_id]["sources"]:
                    scores[book_id]["sources"].append("bm25")
                scores[book_id]["bm25_rank"] = rank

            # 按RRF分数排序
            sorted_results = sorted(
                scores.values(),
                key=lambda x: x["rrf_score"],
                reverse=True
            )

            # 构建输出
            merged = []
            for item in sorted_results:
                merged.append({
                    **item["data"],
                    "rrf_score": round(item["rrf_score"], 4),
                    "sources": item["sources"],
                    "vector_rank": item["vector_rank"],
                    "bm25_rank": item["bm25_rank"]
                })

            logger.info(
                f"RRF融合完成: 路A={len(results_a)}, 路B={len(results_b)}, "
                f"融合后={len(merged)}, k={self.k}"
            )

            return merged

        except Exception as e:
            logger.error(f"RRF融合失败: {str(e)}")
            # 降级：返回第一路结果
            return results_a

    def merge_multi(
        self,
        results_list: List[List[Dict]],
        rank_keys: List[str] = None
    ) -> List[Dict]:
        """
        融合多路检索结果（超过2路）

        Args:
            results_list: 多路结果列表
            rank_keys: 每路结果的排序字段（可选）

        Returns:
            融合后的结果列表
        """
        try:
            if not results_list:
                return []

            # 构建排名映射
            scores = {}

            for idx, results in enumerate(results_list):
                source_name = f"source_{idx}"

                for rank, item in enumerate(results, start=1):
                    book_id = item.get("book_id")
                    if not book_id:
                        continue

                    if book_id not in scores:
                        scores[book_id] = {
                            "data": item,
                            "rrf_score": 0,
                            "sources": [],
                            "ranks": {}
                        }

                    # RRF贡献分数
                    scores[book_id]["rrf_score"] += 1 / (self.k + rank)
                    scores[book_id]["sources"].append(source_name)
                    scores[book_id]["ranks"][source_name] = rank

            # 按RRF分数排序
            sorted_results = sorted(
                scores.values(),
                key=lambda x: x["rrf_score"],
                reverse=True
            )

            # 构建输出
            merged = []
            for item in sorted_results:
                merged.append({
                    **item["data"],
                    "rrf_score": round(item["rrf_score"], 4),
                    "sources": item["sources"],
                    "ranks": item["ranks"]
                })

            logger.info(
                f"RRF多路融合完成: {len(results_list)}路, 融合后={len(merged)}, k={self.k}"
            )

            return merged

        except Exception as e:
            logger.error(f"RRF多路融合失败: {str(e)}")
            # 降级：返回第一路结果
            return results_list[0] if results_list else []

    def set_k(self, k: int):
        """设置平滑常数"""
        self.k = k
        logger.info(f"RRF平滑常数已更新: k={k}")

    def get_k(self) -> int:
        """获取当前平滑常数"""
        return self.k

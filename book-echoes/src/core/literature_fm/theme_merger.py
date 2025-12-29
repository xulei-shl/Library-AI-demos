"""
结果融合器
融合双路召回结果
"""

from typing import Dict, List
from dataclasses import dataclass, field

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MergedResult:
    """融合后的检索结果"""
    book_id: int
    title: str
    author: str
    call_no: str
    tags_json: str = ''
    vector_score: float = 0
    tag_score: float = 0
    final_score: float = 0
    sources: List[str] = field(default_factory=list)


class ThemeMerger:
    """融合双路召回结果"""

    def __init__(self, vector_weight: float = 0.5):
        """
        初始化结果融合器

        Args:
            vector_weight: 向量检索结果权重（标签权重 = 1 - vector_weight）
        """
        self.vector_weight = vector_weight
        self.tag_weight = 1 - vector_weight

    def merge(
        self,
        vector_results: List[Dict],
        tag_results: List[Dict]
    ) -> List[MergedResult]:
        """
        融合向量检索和标签检索的结果

        Args:
            vector_results: 向量检索结果
            tag_results: 标签检索结果

        Returns:
            融合后的排序结果
        """
        # 1. 聚合结果
        aggregated: Dict[int, MergedResult] = {}

        for item in vector_results:
            book_id = item['book_id']
            aggregated[book_id] = MergedResult(
                book_id=book_id,
                title=item.get('title', ''),
                author=item.get('author', ''),
                call_no=item.get('call_no', ''),
                tags_json=item.get('tags_json', ''),
                vector_score=item.get('vector_score', 0),
                sources=['vector']
            )

        for item in tag_results:
            book_id = item['book_id']
            if book_id in aggregated:
                # 已存在，合并分数和来源
                aggregated[book_id].tag_score = item.get('tag_score', 0)
                if 'tag' not in aggregated[book_id].sources:
                    aggregated[book_id].sources.append('tag')
            else:
                # 新条目
                aggregated[book_id] = MergedResult(
                    book_id=book_id,
                    title=item.get('title', ''),
                    author=item.get('author', ''),
                    call_no=item.get('call_no', ''),
                    tags_json=item.get('tags_json', ''),
                    tag_score=item.get('tag_score', 0),
                    sources=['tag']
                )

        # 2. 计算综合分数
        for result in aggregated.values():
            result.final_score = (
                self.vector_weight * result.vector_score +
                self.tag_weight * result.tag_score
            )

        # 3. 按分数排序
        sorted_results = sorted(
            aggregated.values(),
            key=lambda x: x.final_score,
            reverse=True
        )

        logger.info(
            f"结果融合完成: 向量={len(vector_results)}, 标签={len(tag_results)}, "
            f"融合后={len(sorted_results)}"
        )

        return sorted_results

    def to_dict_list(self, results: List[MergedResult]) -> List[Dict]:
        """将 MergedResult 转换为字典列表"""
        return [
            {
                'book_id': r.book_id,
                'title': r.title,
                'author': r.author,
                'call_no': r.call_no,
                'tags_json': r.tags_json,
                'vector_score': r.vector_score,
                'tag_score': r.tag_score,
                'final_score': round(r.final_score, 4),
                'sources': r.sources
            }
            for r in results
        ]

"""文章聚类器，负责将相似文章分组。"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Type

from src.utils.logger import get_logger


class Clusterer:
    """基于 TF-IDF 与层次聚类的文章聚类器。

    使用 AgglomerativeClustering 通过距离阈值自动确定分组数量，
    无需预设簇数，更适合小数据集（10-50篇文章）。
    """

    def __init__(
        self,
        distance_threshold: float = 0.8,
        batch_size: int = 6,  # 保留用于降级分组
        vectorizer_cls: Optional[Type] = None,
        clustering_cls: Optional[Type] = None,
    ):
        """
        Args:
            distance_threshold: 距离阈值，控制分组粒度。
                               越小分组越细（0.5~1.2，推荐0.8）。
            batch_size: 降级时使用的批次大小。
        """
        self.distance_threshold = distance_threshold
        self.batch_size = max(1, batch_size)
        self.logger = get_logger(__name__)
        self._vectorizer_cls = vectorizer_cls
        self._clustering_cls = clustering_cls

    def cluster(self, articles: Sequence[Dict]) -> List[List[Dict]]:
        """
        使用层次聚类（AgglomerativeClustering）自动分组。

        Args:
            articles: 预处理后的文章列表，需包含 summary_long 等字段。

        Returns:
            聚类后的文章二维数组，每个子列表是一组文章。
        """
        if not articles:
            self.logger.warning("文章列表为空，直接返回空分组")
            return []

        # 只有1篇文章时直接返回
        if len(articles) == 1:
            self.logger.info("仅1篇文章，直接归为同一组")
            return [list(articles)]

        vectorizer_cls = self._vectorizer_cls
        clustering_cls = self._clustering_cls
        if vectorizer_cls is None or clustering_cls is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.cluster import AgglomerativeClustering
            except ImportError:
                self.logger.warning("scikit-learn 未安装，退化为按批次平均分组")
                return self._chunk_by_batch(articles)
            vectorizer_cls = TfidfVectorizer
            clustering_cls = AgglomerativeClustering

        feature_texts = [self._build_feature_text(article, idx) for idx, article in enumerate(articles)]
        vectorizer = vectorizer_cls(max_features=4096, ngram_range=(1, 2))
        try:
            tfidf_matrix = vectorizer.fit_transform(feature_texts)

            # 使用层次聚类，通过距离阈值自动确定分组数
            model = clustering_cls(
                n_clusters=None,  # 不预设簇数
                distance_threshold=self.distance_threshold,
                metric="cosine",  # 余弦相似度，适合文本
                linkage="average",  # 平均链接
            )

            # AgglomerativeClustering 需要密集矩阵
            labels = model.fit_predict(tfidf_matrix.toarray())

            grouped: Dict[int, List[Dict]] = defaultdict(list)
            for article, label in zip(articles, labels):
                grouped[int(label)].append(article)

            groups = list(grouped.values())
            self.logger.info(
                f"层次聚类完成，共生成 {len(groups)} 个分组 "
                f"(distance_threshold={self.distance_threshold})"
            )
            return groups
        except Exception as exc:  # pragma: no cover - 极端情况
            self.logger.error(f"层次聚类失败，退化为按批次分组: {exc}")
            return self._chunk_by_batch(articles)

    def _build_feature_text(self, article: Dict, index: int) -> str:
        """拼接特征字段，作为向量化的输入文本。

        优化策略：
        - 使用 topic_focus（主题聚焦点，50字，用于聚类）作为核心特征
        - 优先使用 full_text 前2000字（特征丰富），fallback 到 summary_long
        - 移除 llm_thematic_essence（太抽象，干扰聚类）
        - title、topic_focus 和 tags 重复以提高权重
        """
        title = str(article.get("title") or f"文章{index+1}")

        # 主题聚焦点（50字，用于聚类，权重高）
        topic_focus = str(article.get("llm_topic_focus") or "")

        # 优先用 full_text 前1000字，fallback 到 summary_long
        # full_text 包含完整文章内容，特征更丰富；截取前2000字避免性能问题和尾部噪音
        raw_content = str(article.get("full_text") or "")[:2000]
        if not raw_content.strip():
            raw_content = str(article.get("summary_long") or "")

        # LLM 标签（具体，权重高）
        tags = article.get("llm_tags") or ""
        if isinstance(tags, (list, tuple, set)):
            tags_text = " ".join(str(tag) for tag in tags)
        else:
            tags_text = str(tags)

        # LLM 长摘要（适中权重）
        summary_long = str(article.get("summary_long") or "")

        # 提及的书籍
        mentioned = article.get("llm_mentioned_books") or ""
        mentioned_text = " ".join(mentioned) if isinstance(mentioned, (list, tuple, set)) else str(mentioned)

        # 注意：移除 thematic_essence，因为太抽象会干扰聚类
        # 标签、标题和主题聚焦点重复以提高权重
        return " ".join(filter(None, [
            title, title,                       # 标题权重 x2
            topic_focus, topic_focus, topic_focus,  # 主题聚焦点权重 x3（聚类核心特征）
            raw_content,                        # 原始内容（full_text前2000字或summary_long）
            tags_text, tags_text,               # 标签权重 x2
            summary_long,
            mentioned_text,
        ]))

    def _chunk_by_batch(self, articles: Sequence[Dict]) -> List[List[Dict]]:
        """按 batch_size 顺序切分列表。"""
        chunked: List[List[Dict]] = []
        batch = max(1, self.batch_size)
        for idx in range(0, len(articles), batch):
            chunked.append(list(articles[idx: idx + batch]))
        return chunked or [list(articles)]

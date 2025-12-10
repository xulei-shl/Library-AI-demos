"""文章聚类器，负责将相似文章分组。"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Type

from src.utils.logger import get_logger


class Clusterer:
    """基于 TF-IDF 与 KMeans 的文章聚类器。"""

    def __init__(
        self,
        batch_size: int = 6,
        vectorizer_cls: Optional[Type] = None,
        kmeans_cls: Optional[Type] = None,
    ):
        """
        Args:
            batch_size: 预期每组文章数量，用于动态估算聚类数。
        """
        self.batch_size = max(1, batch_size)
        self.logger = get_logger(__name__)
        self._vectorizer_cls = vectorizer_cls
        self._kmeans_cls = kmeans_cls

    def cluster(self, articles: Sequence[Dict]) -> List[List[Dict]]:
        """
        Args:
            articles: 预处理后的文章列表，需包含 summary_long 等字段。

        Returns:
            聚类后的文章二维数组，每个子列表是一组文章。

        Raises:
            RuntimeError: 当缺少 scikit-learn 依赖时抛出。
        """
        if not articles:
            self.logger.warning("文章列表为空，直接返回空分组")
            return []

        vectorizer_cls = self._vectorizer_cls
        kmeans_cls = self._kmeans_cls
        if vectorizer_cls is None or kmeans_cls is None:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.cluster import KMeans
            except ImportError:
                self.logger.warning("scikit-learn 未安装，退化为按批次平均分组")
                return self._chunk_by_batch(articles)
            vectorizer_cls = TfidfVectorizer
            kmeans_cls = KMeans

        feature_texts = [self._build_feature_text(article, idx) for idx, article in enumerate(articles)]
        vectorizer = vectorizer_cls(max_features=4096, ngram_range=(1, 2))
        try:
            tfidf_matrix = vectorizer.fit_transform(feature_texts)

            cluster_count = self._estimate_cluster_count(len(articles))

            if cluster_count == 1:
                self.logger.info("文章数量不足以划分多个簇，全部归为同一组")
                return [list(articles)]

            model = kmeans_cls(
                n_clusters=cluster_count,
                n_init="auto",
                random_state=42,
                max_iter=300,
            )
            labels = model.fit_predict(tfidf_matrix)

            grouped: Dict[int, List[Dict]] = defaultdict(list)
            for article, label in zip(articles, labels):
                grouped[int(label)].append(article)

            groups = list(grouped.values())
            self.logger.info(f"聚类完成，共生成 {len(groups)} 个分组")
            return groups
        except Exception as exc:  # pragma: no cover - 极端情况
            self.logger.error(f"TF-IDF 聚类失败，退化为按批次分组: {exc}")
            return self._chunk_by_batch(articles)

    def _estimate_cluster_count(self, total: int) -> int:
        """根据文章数量与批次大小估算簇数量。"""
        if total <= self.batch_size:
            return 1
        clusters = total // self.batch_size
        if total % self.batch_size:
            clusters += 1
        return max(1, min(total, clusters))

    def _build_feature_text(self, article: Dict, index: int) -> str:
        """拼接特征字段，作为向量化的输入文本。"""
        title = str(article.get("title") or f"文章{index+1}")
        essence = str(article.get("llm_thematic_essence") or "")
        tags = article.get("llm_tags") or ""
        if isinstance(tags, (list, tuple, set)):
            tags_text = " ".join(str(tag) for tag in tags)
        else:
            tags_text = str(tags)
        summary = str(article.get("summary_long") or "")
        mentioned = article.get("llm_mentioned_books") or ""
        mentioned_text = " ".join(mentioned) if isinstance(mentioned, (list, tuple, set)) else str(mentioned)
        return " ".join(filter(None, [title, essence, tags_text, summary, mentioned_text]))

    def _chunk_by_batch(self, articles: Sequence[Dict]) -> List[List[Dict]]:
        """按 batch_size 顺序切分列表。"""
        chunked: List[List[Dict]] = []
        batch = max(1, self.batch_size)
        for idx in range(0, len(articles), batch):
            chunked.append(list(articles[idx: idx + batch]))
        return chunked or [list(articles)]

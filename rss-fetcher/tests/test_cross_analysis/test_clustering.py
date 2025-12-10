"""Clusterer 单元测试"""

import pytest

from src.core.cross_analysis.clustering import Clusterer


class DummyVectorizer:
    """替代 TfidfVectorizer 的简易实现。"""

    def __init__(self, **_kwargs):
        self.captured = []

    def fit_transform(self, texts):
        self.captured = list(texts)
        return list(range(len(texts)))


class DummyKMeans:
    """替代 KMeans 的简易实现。"""

    def __init__(self, n_clusters: int, **_kwargs):
        self.n_clusters = n_clusters

    def fit_predict(self, indexes):
        return [idx % self.n_clusters for idx in indexes]


class ExplosiveVectorizer(DummyVectorizer):
    """模拟向量化失败的场景。"""

    def fit_transform(self, texts):
        raise ValueError("intentional failure")


@pytest.fixture
def sample_articles():
    """构造示例文章数据。"""
    return [
        {
            "title": f"文章{i}",
            "llm_thematic_essence": "主题A" if i % 2 == 0 else "主题B",
            "llm_tags": ["科技", "教育"],
            "summary_long": "人工智能与教育融合的探索",
            "llm_mentioned_books": ["AI 变革"],
        }
        for i in range(6)
    ]


def test_clusterer_grouping(sample_articles):
    """验证依赖注入后的聚类行为。"""
    clusterer = Clusterer(batch_size=3, vectorizer_cls=DummyVectorizer, kmeans_cls=DummyKMeans)
    groups = clusterer.cluster(sample_articles)
    assert len(groups) == 2
    assert sum(len(group) for group in groups) == 6


def test_clusterer_fallback(sample_articles):
    """当向量化失败时应退化为按批次切分。"""
    clusterer = Clusterer(batch_size=2, vectorizer_cls=ExplosiveVectorizer, kmeans_cls=DummyKMeans)
    groups = clusterer.cluster(sample_articles)
    assert len(groups) == 3
    assert all(len(group) <= 2 for group in groups)

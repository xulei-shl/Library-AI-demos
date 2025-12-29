"""
图书向量化预处理模块

该模块负责将SQLite数据库中的图书数据向量化并存储到ChromaDB，
为后续的语义检索和推荐功能提供基础。
"""

from .vectorizer import BookVectorizer
from .retriever import BookRetriever

__all__ = ['BookVectorizer', 'BookRetriever']

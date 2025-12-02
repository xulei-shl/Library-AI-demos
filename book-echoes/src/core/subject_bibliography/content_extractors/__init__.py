"""全文提取器模块"""

from .base import BaseContentExtractor
from .factory import ExtractorFactory
from .pengpai import PengpaiExtractor
from .bigthink import BigThinkExtractor
from .wikipedia import WikipediaExtractor

# 注册所有提取器
ExtractorFactory.register(PengpaiExtractor)
ExtractorFactory.register(BigThinkExtractor)
ExtractorFactory.register(WikipediaExtractor)

__all__ = [
    "BaseContentExtractor",
    "ExtractorFactory",
    "PengpaiExtractor",
    "BigThinkExtractor",
    "WikipediaExtractor",
]

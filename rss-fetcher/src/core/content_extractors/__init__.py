"""全文提取器模块"""

from .base import BaseContentExtractor
from .factory import ExtractorFactory
from .pengpai import PengpaiExtractor
from .pengpai_playwright import PengpaiPlaywrightExtractor
from .bigthink import BigThinkExtractor
from .bigthink_official import BigThinkOfficialExtractor
from .wikipedia import WikipediaExtractor
from .wewe import WeweExtractor

# 注册所有提取器 - Playwright提取器优先注册
ExtractorFactory.register(PengpaiPlaywrightExtractor)
ExtractorFactory.register(BigThinkOfficialExtractor)
ExtractorFactory.register(WikipediaExtractor)
ExtractorFactory.register(WeweExtractor)
ExtractorFactory.register(BigThinkExtractor)
ExtractorFactory.register(PengpaiExtractor)  # 作为备用方案最后注册

__all__ = [
    "BaseContentExtractor",
    "ExtractorFactory",
    "PengpaiExtractor",
    "PengpaiPlaywrightExtractor",
    "BigThinkExtractor",
    "BigThinkOfficialExtractor",
    "WikipediaExtractor",
    "WeweExtractor",
]

"""
模块8: 文学情境推荐 (LiteratureFM - 文学FM)
Phase 2: LLM打标功能
Phase 2.5: 文学策划主题生成
Phase 3: 情境主题检索功能
"""

from .literature_fm_orchestrator import LiteratureFMPipeline
from .llm_tagger import LLMTagger
from .tag_manager import TagManager
from .theme_generator import ThemeGenerator
from .cli import LiteratureFMCLI
from .theme_deduplicator import ThemeDeduplicator
from .theme_exporter import ThemeExporter

__all__ = [
    'LiteratureFMPipeline',
    'LLMTagger',
    'TagManager',
    # Phase 2.5
    'ThemeGenerator',
    'LiteratureFMCLI',
    # Phase 3
    'VectorSearcher',
    'ThemeDeduplicator',
    'ThemeExporter',
]

"""
模块8: 文学情境推荐 (LiteratureFM - 文学FM)
Phase 2: LLM打标功能
"""

from .pipeline import LiteratureFMPipeline
from .llm_tagger import LLMTagger
from .tag_manager import TagManager

__all__ = [
    'LiteratureFMPipeline',
    'LLMTagger',
    'TagManager',
]

from typing import Any, Dict, List, Optional
import time

from .....utils.logger import get_logger
from .alias_extraction import AliasExtractor
from .base import InternalAPIRouter

logger = get_logger(__name__)


class AliasSearchManager:
    """别名检索管理器，协调整个别名检索流程"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.alias_extractor = AliasExtractor(settings)
        self.config = settings.get("alias_search", {}) or {}

    def search_with_aliases(
        self,
        entity_label: str,
        entity_type: str,
        context_hint: str,
        wikipedia_data: Optional[Dict[str, Any]],
        api_router: InternalAPIRouter,
        original_candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        使用别名进行检索

        Args:
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            wikipedia_data: Wikipedia数据（包含description）
            api_router: 内部API路由器
            original_candidates: 原始检索结果

        Returns:
            检索结果，包含matched、selected、confidence等字段
        """
        # 1. 检查是否应该尝试别名检索
        if not self._should_attempt_alias_search(entity_type, original_candidates, wikipedia_data, api_router):
            return {
                "matched": False,
                "selected": None,
                "confidence": 0.0,
                "reason": "不满足别名检索条件",
                "alias_used": None,
                "alias_attempts": 0,
            }

        # 2. 提取Wikipedia描述
        wikipedia_description = ""
        if wikipedia_data and isinstance(wikipedia_data, dict):
            wikipedia_description = wikipedia_data.get("description") or ""

        if not wikipedia_description:
            logger.info(f"alias_search_skipped label={entity_label} reason=no_wikipedia_description")
            return {
                "matched": False,
                "selected": None,
                "confidence": 0.0,
                "reason": "无Wikipedia描述",
                "alias_used": None,
                "alias_attempts": 0,
            }

        # 3. 提取并过滤别名
        aliases = self._extract_and_filter_aliases(entity_label, entity_type, context_hint, wikipedia_description)
        if not aliases:
            logger.info(f"alias_search_skipped label={entity_label} reason=no_aliases_extracted")
            return {
                "matched": False,
                "selected": None,
                "confidence": 0.0,
                "reason": "未提取到有效别名",
                "alias_used": None,
                "alias_attempts": 0,
            }

        # 4. 依次尝试别名检索
        max_attempts = min(len(aliases), int(self.config.get("max_alias_attempts", 3)))
        rate_limit_ms = int(self.config.get("rate_limit_ms", 1000))

        for i, alias_data in enumerate(aliases[:max_attempts]):
            alias = alias_data.get("alias")
            confidence = float(alias_data.get("confidence", 0.0))

            # 置信度过滤
            min_confidence = float(self.config.get("min_confidence_threshold", 0.6))
            if not alias or confidence < min_confidence:
                logger.info(
                    f"alias_skipped_low_confidence label={entity_label} alias={alias} confidence={confidence}"
                )
                continue

            logger.info(
                f"alias_search_attempt label={entity_label} alias={alias} confidence={confidence} attempt={i+1}/{max_attempts}"
            )

            try:
                # 使用别名检索候选
                alias_candidates = api_router.route_to_api(entity_type, alias, "zh", entity_type)
                if not alias_candidates:
                    continue

                # 使用 LLM 判断匹配
                from ...entity_matcher import judge_best_match

                judge = judge_best_match(
                    label=entity_label,  # 使用原始标签进行判断
                    ent_type=entity_type,
                    context_hint=context_hint,
                    source="internal_api",
                    candidates=alias_candidates,
                    settings=self.settings,
                )

                if judge.get("matched"):
                    sel = judge.get("selected") or {}
                    logger.info(
                        f"alias_search_success label={entity_label} alias={alias} uri={sel.get('uri')} confidence={judge.get('confidence')}"
                    )
                    return {
                        "matched": True,
                        "selected": sel,
                        "confidence": judge.get("confidence"),
                        "reason": f"使用别名'{alias}'匹配成功: {judge.get('reason')}",
                        "alias_used": alias,
                        "alias_attempts": i + 1,
                        "model": judge.get("model"),
                    }

            except Exception as e:
                logger.warning(f"alias_search_error label={entity_label} alias={alias} err={e}")
                continue

            # 速率限制
            if rate_limit_ms > 0 and i < max_attempts - 1:
                try:
                    time.sleep(rate_limit_ms / 1000.0)
                except Exception:
                    pass

        # 5. 所有别名都尝试失败
        logger.info(f"alias_search_failed label={entity_label} attempts={max_attempts}")
        return {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": f"尝试了{max_attempts}个别名，均未匹配",
            "alias_used": None,
            "alias_attempts": max_attempts,
        }

    def _should_attempt_alias_search(
        self,
        entity_type: str,
        original_result: List[Dict[str, Any]],
        wikipedia_data: Optional[Dict[str, Any]],
        api_router: InternalAPIRouter,
    ) -> bool:
        """判断是否应该尝试别名检索"""
        # 全局开关
        if not bool(self.config.get("enabled", True)):
            return False

        # 特定API开关：tools.{api}.enable_alias_search
        api_name = api_router.get_api_name(entity_type)
        if not api_name:
            return False
        api_cfg = (self.settings.get("tools") or {}).get(api_name) or {}
        if not bool(api_cfg.get("enabled", True)):
            # API 完全禁用则不尝试
            return False
        if not bool(api_cfg.get("enable_alias_search", True)):
            # 别名检索开关关闭
            return False

        # Wikipedia存在且有描述
        if not wikipedia_data or not isinstance(wikipedia_data, dict):
            return False
        if not wikipedia_data.get("description"):
            return False

        return True

    def _extract_and_filter_aliases(
        self,
        entity_label: str,
        entity_type: str,
        context_hint: str,
        wikipedia_description: str,
    ) -> List[Dict[str, Any]]:
        """提取并过滤别名，按置信度降序排序"""
        try:
            aliases_data = self.alias_extractor.extract_aliases(
                entity_label, entity_type, context_hint, wikipedia_description
            )

            min_confidence = float(self.config.get("min_confidence_threshold", 0.6))
            filtered_aliases = [
                alias_data
                for alias_data in aliases_data
                if float(alias_data.get("confidence", 0.0)) >= min_confidence
            ]

            filtered_aliases.sort(key=lambda x: float(x.get("confidence", 0.0)), reverse=True)

            preview = [a.get("alias") for a in filtered_aliases[:3]]
            logger.info(
                f"aliases_extracted label={entity_label} total={len(aliases_data)} filtered={len(filtered_aliases)} top={preview}"
            )

            return filtered_aliases
        except Exception as e:
            logger.warning(f"alias_extraction_failed label={entity_label} err={e}")
            return []
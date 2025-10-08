# 别名检索实现细节

## 概述

本文档描述了别名检索循环逻辑的具体实现细节，包括别名提取、检索循环、错误处理和测试用例设计。

## 别名提取实现

### 1. AliasExtractor 类实现

```python
# src/core/l2_knowledge_linking/tools/alias_extraction.py

import json
import os
from typing import Any, Dict, List

from ...utils.logger import get_logger
from ...utils.llm_api import invoke_model
from ...utils.json_repair import repair_json_output

logger = get_logger(__name__)

class AliasExtractor:
    """别名提取器，从Wikipedia描述中提取实体别名"""
    
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.config = settings.get("alias_search", {})
        
    def extract_aliases(self, 
                       entity_label: str, 
                       entity_type: str, 
                       context_hint: str, 
                       wikipedia_description: str) -> List[Dict[str, Any]]:
        """
        从Wikipedia描述中提取别名
        
        Args:
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            wikipedia_description: Wikipedia描述文本
            
        Returns:
            别名列表，每个别名包含alias、reason、confidence字段
        """
        try:
            messages = self._build_extraction_messages(
                entity_label, entity_type, context_hint, wikipedia_description
            )
            
            output = invoke_model("l2_alias_extraction", messages, self.settings)
            aliases = self._parse_extraction_output(output)
            
            logger.info(f"alias_extraction_completed label={entity_label} count={len(aliases)}")
            return aliases
            
        except Exception as e:
            logger.warning(f"alias_extraction_failed label={entity_label} err={e}")
            return []
    
    def _build_extraction_messages(self, 
                                  entity_label: str, 
                                  entity_type: str, 
                                  context_hint: str, 
                                  wikipedia_description: str) -> List[Dict[str, Any]]:
        """构建别名提取的大模型消息"""
        # 读取提示词
        prompts_dir = os.path.join("src", "prompts")
        prompt_path = os.path.join(prompts_dir, "l2_alias_extraction.md")
        
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except Exception as e:
            logger.error(f"failed_to_read_alias_prompt path={prompt_path} err={e}")
            system_prompt = "请从给定的Wikipedia描述中提取实体的各种别名形式。"
        
        # 替换占位符
        system_prompt = system_prompt.replace("{entity_label}", entity_label)
        system_prompt = system_prompt.replace("{entity_type}", entity_type)
        system_prompt = system_prompt.replace("{context_hint}", context_hint)
        system_prompt = system_prompt.replace("{wikipedia_description}", wikipedia_description)
        
        user_content = f"""请从以下Wikipedia描述中为实体"{entity_label}"（类型：{entity_type}）提取别名：

{wikipedia_description}

请按照提示词要求输出JSON格式的结果。"""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    
    def _parse_extraction_output(self, output: str) -> List[Dict[str, Any]]:
        """解析大模型输出的别名提取结果"""
        try:
            # 尝试直接解析JSON
            data = json.loads(output)
            aliases = data.get("aliases", [])
            
            # 验证和标准化别名数据
            valid_aliases = []
            for alias_data in aliases:
                if isinstance(alias_data, dict):
                    alias = alias_data.get("alias", "").strip()
                    reason = alias_data.get("reason", "").strip()
                    confidence = alias_data.get("confidence", 0.0)
                    
                    if alias and isinstance(confidence, (int, float)):
                        valid_aliases.append({
                            "alias": alias,
                            "reason": reason,
                            "confidence": float(confidence)
                        })
            
            return valid_aliases
            
        except Exception as e:
            logger.warning(f"json_parse_failed err={e}, attempting repair")
            
            # 尝试修复JSON
            repaired_data = repair_json_output(output)
            if repaired_data:
                try:
                    aliases = repaired_data.get("aliases", [])
                    valid_aliases = []
                    for alias_data in aliases:
                        if isinstance(alias_data, dict):
                            alias = alias_data.get("alias", "").strip()
                            reason = alias_data.get("reason", "").strip()
                            confidence = alias_data.get("confidence", 0.0)
                            
                            if alias and isinstance(confidence, (int, float)):
                                valid_aliases.append({
                                    "alias": alias,
                                    "reason": reason,
                                    "confidence": float(confidence)
                                })
                    
                    return valid_aliases
                except Exception:
                    pass
            
            logger.error(f"alias_extraction_parse_failed output={output[:200]}...")
            return []
```

## 别名检索循环逻辑

### 1. 循环控制逻辑

```python
def _execute_alias_search_loop(self, 
                              entity_label: str, 
                              entity_type: str, 
                              context_hint: str,
                              aliases: List[Dict[str, Any]],
                              api_router: InternalAPIRouter) -> Dict[str, Any]:
    """
    执行别名检索循环
    
    Args:
        entity_label: 实体标签
        entity_type: 实体类型
        context_hint: 上下文提示
        aliases: 别名列表
        api_router: 内部API路由器
        
    Returns:
        检索结果字典
    """
    max_attempts = min(len(aliases), self.config.get("max_alias_attempts", 3))
    rate_limit_ms = self.config.get("rate_limit_ms", 1000)
    
    for i, alias_data in enumerate(aliases[:max_attempts]):
        alias = alias_data.get("alias")
        confidence = alias_data.get("confidence", 0.0)
        
        # 置信度过滤
        min_confidence = self.config.get("min_confidence_threshold", 0.6)
        if confidence < min_confidence:
            logger.info(f"alias_skipped_low_confidence label={entity_label} alias={alias} confidence={confidence}")
            continue
        
        logger.info(f"alias_search_attempt label={entity_label} alias={alias} confidence={confidence} attempt={i+1}/{max_attempts}")
        
        try:
            # 执行别名检索
            result = self._attempt_single_alias_search(
                entity_label, entity_type, context_hint, alias, api_router
            )
            
            if result.get("matched"):
                result["alias_used"] = alias
                result["alias_attempts"] = i + 1
                return result
            
        except Exception as e:
            logger.warning(f"alias_search_error label={entity_label} alias={alias} err={e}")
            continue
        
        # 速率限制
        if rate_limit_ms > 0 and i < max_attempts - 1:
            try:
                time.sleep(rate_limit_ms / 1000.0)
            except Exception:
                pass
    
    # 所有别名都尝试失败
    return {
        "matched": False,
        "selected": None,
        "confidence": 0.0,
        "reason": f"尝试了{max_attempts}个别名，均未匹配",
        "alias_used": None,
        "alias_attempts": max_attempts
    }

def _attempt_single_alias_search(self, 
                                entity_label: str, 
                                entity_type: str, 
                                context_hint: str,
                                alias: str,
                                api_router: InternalAPIRouter) -> Dict[str, Any]:
    """
    尝试单个别名的检索
    
    Args:
        entity_label: 原始实体标签
        entity_type: 实体类型
        context_hint: 上下文提示
        alias: 要尝试的别名
        api_router: 内部API路由器
        
    Returns:
        检索结果字典
    """
    # 1. 使用别名检索
    alias_candidates = api_router.route_to_api(entity_type, alias, "zh", entity_type)
    
    if not alias_candidates:
        return {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": f"别名'{alias}'检索无结果"
        }
    
    # 2. LLM判断
    from ...entity_matcher import judge_best_match
    judge = judge_best_match(
        label=entity_label,  # 使用原始标签进行判断
        ent_type=entity_type,
        context_hint=context_hint,
        source="internal_api",
        candidates=alias_candidates,
        settings=self.settings
    )
    
    if judge.get("matched"):
        sel = judge.get("selected") or {}
        return {
            "matched": True,
            "selected": sel,
            "confidence": judge.get("confidence"),
            "reason": f"使用别名'{alias}'匹配成功: {judge.get('reason')}",
            "model": judge.get("model")
        }
    else:
        return {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": f"别名'{alias}'LLM判断不匹配: {judge.get('reason')}"
        }
```

## 错误处理和日志记录

### 1. 错误分类和处理

```python
class AliasSearchError(Exception):
    """别名检索错误基类"""
    pass

class AliasExtractionError(AliasSearchError):
    """别名提取错误"""
    pass

class AliasSearchTimeoutError(AliasSearchError):
    """别名检索超时错误"""
    pass

class AliasSearchConfigError(AliasSearchError):
    """别名检索配置错误"""
    pass

def _handle_alias_search_error(self, 
                              error: Exception, 
                              entity_label: str, 
                              alias: str = None) -> Dict[str, Any]:
    """
    统一处理别名检索错误
    
    Args:
        error: 错误对象
        entity_label: 实体标签
        alias: 当前尝试的别名（可选）
        
    Returns:
        错误结果字典
    """
    error_msg = str(error)
    alias_info = f" alias={alias}" if alias else ""
    
    if isinstance(error, AliasExtractionError):
        logger.error(f"alias_extraction_error label={entity_label}{alias_info} err={error_msg}")
        return {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": f"别名提取失败: {error_msg}",
            "alias_used": alias,
            "alias_attempts": 0,
            "error_type": "extraction_error"
        }
    
    elif isinstance(error, AliasSearchTimeoutError):
        logger.error(f"alias_search_timeout label={entity_label}{alias_info} err={error_msg}")
        return {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": f"别名检索超时: {error_msg}",
            "alias_used": alias,
            "alias_attempts": 0,
            "error_type": "timeout_error"
        }
    
    elif isinstance(error, AliasSearchConfigError):
        logger.error(f"alias_search_config_error label={entity_label}{alias_info} err={error_msg}")
        return {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": f"别名检索配置错误: {error_msg}",
            "alias_used": alias,
            "alias_attempts": 0,
            "error_type": "config_error"
        }
    
    else:
        logger.error(f"alias_search_unknown_error label={entity_label}{alias_info} err={error_msg}")
        return {
            "matched": False,
            "selected": None,
            "confidence": 0.0,
            "reason": f"未知错误: {error_msg}",
            "alias_used": alias,
            "alias_attempts": 0,
            "error_type": "unknown_error"
        }
```

### 2. 详细日志记录

```python
def _log_alias_search_start(self, entity_label: str, entity_type: str, wikipedia_description: str):
    """记录别名检索开始"""
    desc_len = len(wikipedia_description)
    logger.info(f"alias_search_started label={entity_label} type={entity_type} desc_len={desc_len}")

def _log_aliases_extracted(self, entity_label: str, aliases: List[Dict[str, Any]]):
    """记录别名提取结果"""
    total_count = len(aliases)
    if total_count > 0:
        top_aliases = [a.get("alias", "") for a in aliases[:3]]
        logger.info(f"aliases_extracted label={entity_label} count={total_count} top_aliases={top_aliases}")
    else:
        logger.info(f"no_aliases_extracted label={entity_label}")

def _log_alias_attempt(self, entity_label: str, alias: str, confidence: float, attempt: int, total: int):
    """记录单个别名尝试"""
    logger.info(f"alias_attempt label={entity_label} alias='{alias}' confidence={confidence} attempt={attempt}/{total}")

def _log_alias_success(self, entity_label: str, alias: str, selected_uri: str, confidence: float):
    """记录别名检索成功"""
    logger.info(f"alias_success label={entity_label} alias='{alias}' uri={selected_uri} confidence={confidence}")

def _log_alias_failure(self, entity_label: str, attempts: int, reason: str):
    """记录别名检索失败"""
    logger.info(f"alias_failed label={entity_label} attempts={attempts} reason='{reason}'")
```

## 单元测试设计

### 1. 测试用例结构

```python
# tests/core/l2_knowledge_linking/test_alias_search.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.core.l2_knowledge_linking.tools.alias_extraction import AliasExtractor
from src.core.l2_knowledge_linking.tools.alias_search_manager import AliasSearchManager

class TestAliasExtractor:
    """别名提取器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.settings = {
            "alias_search": {
                "enabled": True,
                "max_alias_attempts": 3,
                "min_confidence_threshold": 0.6
            },
            "tasks": {
                "l2_alias_extraction": {
                    "model": "test-model"
                }
            }
        }
        self.extractor = AliasExtractor(self.settings)
    
    def test_extract_aliases_success(self):
        """测试成功提取别名"""
        # 模拟LLM返回
        mock_output = '''
        {
            "aliases": [
                {
                    "alias": "巴金",
                    "reason": "本名",
                    "confidence": 0.95
                },
                {
                    "alias": "李尧棠",
                    "reason": "本名",
                    "confidence": 0.9
                }
            ],
            "extraction_summary": "成功提取2个别名"
        }
        '''
        
        with patch('src.core.l2_knowledge_linking.tools.alias_extraction.invoke_model') as mock_invoke:
            mock_invoke.return_value = mock_output
            
            result = self.extractor.extract_aliases(
                "巴金", "person", "著名作家", "巴金（1904年11月25日—2005年10月17日），原名李尧棠..."
            )
            
            assert len(result) == 2
            assert result[0]["alias"] == "巴金"
            assert result[0]["confidence"] == 0.95
            assert result[1]["alias"] == "李尧棠"
            assert result[1]["confidence"] == 0.9
    
    def test_extract_aliases_empty_result(self):
        """测试提取结果为空"""
        mock_output = '{"aliases": [], "extraction_summary": "未找到别名"}'
        
        with patch('src.core.l2_knowledge_linking.tools.alias_extraction.invoke_model') as mock_invoke:
            mock_invoke.return_value = mock_output
            
            result = self.extractor.extract_aliases(
                "未知人物", "person", "", "简短描述"
            )
            
            assert len(result) == 0
    
    def test_extract_aliases_json_error(self):
        """测试JSON解析错误"""
        mock_output = 'invalid json output'
        
        with patch('src.core.l2_knowledge_linking.tools.alias_extraction.invoke_model') as mock_invoke:
            mock_invoke.return_value = mock_output
            
            result = self.extractor.extract_aliases(
                "测试人物", "person", "", "测试描述"
            )
            
            assert len(result) == 0

class TestAliasSearchManager:
    """别名检索管理器测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.settings = {
            "alias_search": {
                "enabled": True,
                "max_alias_attempts": 3,
                "min_confidence_threshold": 0.6,
                "rate_limit_ms": 0  # 测试时不延迟
            }
        }
        self.manager = AliasSearchManager(self.settings)
    
    def test_should_attempt_alias_search(self):
        """测试是否应该尝试别名检索的条件判断"""
        # 测试满足条件的情况
        wikipedia_data = {"description": "有效的Wikipedia描述"}
        result = self.manager._should_attempt_alias_search("person", [], wikipedia_data)
        assert result is True
        
        # 测试不满足条件的情况
        result = self.manager._should_attempt_alias_search("person", [], None)
        assert result is False
        
        result = self.manager._should_attempt_alias_search("person", [], {})
        assert result is False
    
    def test_extract_and_filter_aliases(self):
        """测试别名提取和过滤"""
        mock_aliases = [
            {"alias": "别名1", "reason": "理由1", "confidence": 0.8},
            {"alias": "别名2", "reason": "理由2", "confidence": 0.5},  # 低于阈值
            {"alias": "别名3", "reason": "理由3", "confidence": 0.9}
        ]
        
        with patch.object(self.manager.alias_extractor, 'extract_aliases') as mock_extract:
            mock_extract.return_value = mock_aliases
            
            result = self.manager._extract_and_filter_aliases(
                "测试实体", "person", "", "测试描述"
            )
            
            # 应该过滤掉低置信度的别名
            assert len(result) == 2
            assert result[0]["alias"] == "别名3"  # 按置信度排序
            assert result[1]["alias"] == "别名1"
    
    @patch('time.sleep')
    def test_search_with_aliases_success(self, mock_sleep):
        """测试别名检索成功"""
        # 模拟别名数据
        mock_aliases = [
            {"alias": "李尧棠", "reason": "本名", "confidence": 0.9}
        ]
        
        # 模拟API路由器
        mock_router = Mock()
        mock_candidates = [{"uri": "test-uri", "label": "巴金", "description": "作家"}]
        mock_router.route_to_api.return_value = mock_candidates
        
        # 模拟LLM判断
        with patch('src.core.l2_knowledge_linking.tools.alias_search_manager.judge_best_match') as mock_judge:
            mock_judge.return_value = {
                "matched": True,
                "selected": {"uri": "test-uri", "label": "巴金"},
                "confidence": 0.95,
                "reason": "匹配成功"
            }
            
            with patch.object(self.manager, '_extract_and_filter_aliases') as mock_extract:
                mock_extract.return_value = mock_aliases
                
                result = self.manager.search_with_aliases(
                    "巴金", "person", "著名作家", 
                    {"description": "巴金，原名李尧棠..."},
                    mock_router, []
                )
                
                assert result["matched"] is True
                assert result["alias_used"] == "李尧棠"
                assert result["alias_attempts"] == 1
    
    def test_search_with_aliases_no_wikipedia(self):
        """测试没有Wikipedia数据的情况"""
        mock_router = Mock()
        
        result = self.manager.search_with_aliases(
            "测试实体", "person", "", None, mock_router, []
        )
        
        assert result["matched"] is False
        assert result["reason"] == "无Wikipedia描述"
        assert result["alias_attempts"] == 0
```

### 2. 集成测试

```python
class TestAliasSearchIntegration:
    """别名检索集成测试"""
    
    def test_end_to_end_alias_search(self):
        """端到端别名检索测试"""
        # 这个测试需要真实的配置和模拟的API响应
        # 测试从Wikipedia描述提取别名到最终匹配的完整流程
        pass
    
    def test_alias_search_with_real_data(self):
        """使用真实数据测试别名检索"""
        # 使用真实的Wikipedia描述和预期的别名进行测试
        pass
```

## 性能测试

### 1. 性能指标

1. **别名提取时间**：从Wikipedia描述提取别名的平均时间
2. **别名检索时间**：每个别名的平均检索时间
3. **成功率**：别名检索的成功率
4. **平均尝试次数**：找到匹配所需的平均别名尝试次数

### 2. 性能测试用例

```python
class TestAliasSearchPerformance:
    """别名检索性能测试"""
    
    def test_alias_extraction_performance(self):
        """测试别名提取性能"""
        # 使用大量Wikipedia描述测试别名提取的性能
        pass
    
    def test_alias_search_performance(self):
        """测试别名检索性能"""
        # 测试多个别名检索的总体性能
        pass
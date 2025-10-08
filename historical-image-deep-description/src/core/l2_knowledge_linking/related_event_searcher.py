"""
相关事件检索与匹配模块

该模块为每个实体检索相关事件，支持：
1. 可配置的关键词重构（使用大模型将实体label重构为检索关键词）
2. 规则性筛选（事件title必须包含检索关键词）
3. 大模型相关性判断（筛选最相关的N个事件）
4. 结果写入实体JSON文件

设计遵循项目的模块化架构，复用现有的：
- event_api 事件API客户端
- entity_matcher LLM判断能力
- 配置化管理机制
"""

import time
from typing import Any, Dict, List, Optional
from ...utils.logger import get_logger
from ...utils.llm_api import invoke_model
from ...utils.json_repair import repair_json_output

logger = get_logger(__name__)


class RelatedEventSearcher:
    """相关事件检索器"""
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化相关事件检索器
        
        Args:
            settings: 全局配置
        """
        self.settings = settings
        self.config = settings.get("related_event_search", {})
        
        # 提取配置参数
        self.enabled = self.config.get("enabled", False)
        self.max_events = int(self.config.get("max_events", 3))
        self.min_confidence = float(self.config.get("min_confidence", 0.7))
        self.title_filter_required = self.config.get("title_filter_required", True)
        self.rate_limit_ms = int(self.config.get("rate_limit_ms", 1000))
        
        # 按实体类型的启用配置
        self.entity_type_config = self.config.get("entity_types", {})
        
        logger.info(f"related_event_searcher_initialized enabled={self.enabled} max_events={self.max_events}")
    
    def is_enabled_for_entity_type(self, entity_type: str) -> bool:
        """
        检查指定实体类型是否启用相关事件检索
        
        Args:
            entity_type: 实体类型
            
        Returns:
            是否启用
        """
        if not self.enabled:
            return False
        
        if not entity_type:
            return False
        
        type_config = self.entity_type_config.get(entity_type, {})
        return type_config.get("enabled", False)
    
    def is_keyword_extraction_enabled(self, entity_type: str) -> bool:
        """
        检查指定实体类型是否启用关键词重构
        
        Args:
            entity_type: 实体类型
            
        Returns:
            是否启用关键词重构
        """
        if not entity_type:
            return False
        
        type_config = self.entity_type_config.get(entity_type, {})
        return type_config.get("enable_keyword_extraction", False)
    
    def search_related_events(
        self, 
        entity_label: str, 
        entity_type: str, 
        context_hint: str = ""
    ) -> Dict[str, Any]:
        """
        为指定实体搜索相关事件
        
        Args:
            entity_label: 实体标签
            entity_type: 实体类型  
            context_hint: 上下文提示
            
        Returns:
            相关事件搜索结果，格式：
            {
                "events": [{"uri": "...", "label": "...", "description": "...", "confidence": 0.9}],
                "metadata": {
                    "search_keyword": "...",  # 实际使用的搜索关键词
                    "keyword_extracted": bool,  # 是否使用了关键词重构
                    "total_candidates": int,    # 总候选数量
                    "filtered_candidates": int, # 规则筛选后的候选数量
                    "executed_at": "...",       # 执行时间
                    "model": "..."              # 使用的模型
                }
            }
        """
        if not self.is_enabled_for_entity_type(entity_type):
            logger.debug(f"related_event_search_disabled type={entity_type} label={entity_label}")
            return {"events": [], "metadata": {"reason": "实体类型未启用相关事件检索"}}
        
        try:
            # Step 1: 生成搜索关键词
            search_keyword, keyword_extracted = self._generate_search_keyword(
                entity_label, entity_type, context_hint
            )
            
            if not search_keyword:
                logger.warning(f"related_event_search_no_keyword type={entity_type} label={entity_label}")
                return {"events": [], "metadata": {"reason": "无法生成搜索关键词"}}
            
            # Step 2: 调用事件API搜索
            event_candidates = self._search_event_api(search_keyword)
            total_candidates = len(event_candidates)
            
            if not event_candidates:
                logger.info(f"related_event_search_no_candidates keyword={search_keyword} label={entity_label}")
                return {
                    "events": [], 
                    "metadata": {
                        "search_keyword": search_keyword,
                        "keyword_extracted": keyword_extracted,
                        "total_candidates": 0,
                        "filtered_candidates": 0,
                        "reason": "未找到候选事件"
                    }
                }
            
            # Step 3: 规则性筛选（事件title必须包含搜索关键词）
            filtered_candidates = self._filter_by_title(event_candidates, search_keyword)
            filtered_count = len(filtered_candidates)
            
            if self.title_filter_required and not filtered_candidates:
                logger.info(f"related_event_search_title_filter_empty keyword={search_keyword} label={entity_label}")
                return {
                    "events": [], 
                    "metadata": {
                        "search_keyword": search_keyword,
                        "keyword_extracted": keyword_extracted,
                        "total_candidates": total_candidates,
                        "filtered_candidates": 0,
                        "reason": "规则筛选后无候选事件"
                    }
                }
            
            # Step 4: 大模型相关性判断
            final_candidates = filtered_candidates if self.title_filter_required else event_candidates
            related_events = self._judge_event_relevance(
                entity_label, entity_type, context_hint, search_keyword, final_candidates
            )
            
            # Step 5: 构建返回结果
            from datetime import datetime
            result = {
                "events": related_events[:self.max_events],
                "metadata": {
                    "search_keyword": search_keyword,
                    "keyword_extracted": keyword_extracted,
                    "total_candidates": total_candidates,
                    "filtered_candidates": filtered_count,
                    "executed_at": datetime.now().isoformat(),
                    "model": self._get_model_name()
                }
            }
            
            logger.info(f"related_event_search_completed label={entity_label} keyword={search_keyword} events_count={len(result['events'])}")
            return result
            
        except Exception as e:
            logger.error(f"related_event_search_error label={entity_label} type={entity_type} error={e}")
            from datetime import datetime
            return {
                "events": [], 
                "metadata": {
                    "error": str(e),
                    "executed_at": datetime.now().isoformat()
                }
            }
        finally:
            # 添加速率限制延时
            if self.rate_limit_ms > 0:
                try:
                    time.sleep(self.rate_limit_ms / 1000.0)
                except Exception:
                    pass
    
    def _generate_search_keyword(
        self, 
        entity_label: str, 
        entity_type: str, 
        context_hint: str
    ) -> tuple[str, bool]:
        """
        生成搜索关键词
        
        Args:
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            
        Returns:
            (搜索关键词, 是否使用了关键词重构)
        """
        # 根据实体类型检查是否启用关键词重构
        enable_extraction = self.is_keyword_extraction_enabled(entity_type)
        
        if not enable_extraction:
            # 直接使用实体标签作为搜索关键词
            logger.debug(f"keyword_extraction_disabled type={entity_type} label={entity_label}")
            return entity_label, False
        
        try:
            # 使用大模型重构关键词
            extracted_keyword = self._extract_keyword_with_llm(
                entity_label, entity_type, context_hint
            )
            
            if extracted_keyword and extracted_keyword.strip():
                logger.debug(f"keyword_extraction_success type={entity_type} original={entity_label} extracted={extracted_keyword.strip()}")
                return extracted_keyword.strip(), True
            else:
                # 重构失败，回退到原始标签
                logger.warning(f"keyword_extraction_failed_fallback type={entity_type} label={entity_label}")
                return entity_label, False
                
        except Exception as e:
            logger.warning(f"keyword_extraction_error_fallback type={entity_type} label={entity_label} error={e}")
            return entity_label, False
    
    def _extract_keyword_with_llm(
        self, 
        entity_label: str, 
        entity_type: str, 
        context_hint: str
    ) -> Optional[str]:
        """
        使用大模型提取关键词
        
        Args:
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            
        Returns:
            提取的关键词
        """
        import os
        
        # 读取关键词提取提示词
        prompt_path = os.path.join("src", "prompts", "l2_event_keyword_extraction.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except Exception as e:
            logger.warning(f"keyword_extraction_prompt_missing path={prompt_path} error={e}")
            system_prompt = """你是一个专业的关键词提取专家。请将实体标签重构为1-2个核心关键词，用于事件检索。

要求：
1. 去除修饰词，保留核心名词
2. 适应事件API的搜索特性
3. 只输出关键词，不要其他内容

示例：
- 输入："话剧《日出》首演" → 输出："话剧 日出"
- 输入："上海戏剧工作社" → 输出："戏剧 上海"
- 输入："卡尔登大戏院" → 输出："卡尔登 戏院"
"""
        
        user_content = f"""请为以下实体提取1-2个核心关键词用于事件检索：

实体标签：{entity_label}
实体类型：{entity_type}
上下文：{context_hint}

请只输出关键词，用空格分隔。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        try:
            output = invoke_model("l2_event_keyword_extraction", messages, self.settings)
            # 简单清理输出
            keyword = output.strip().replace('\n', ' ').replace('\r', ' ')
            # 移除可能的引号
            keyword = keyword.strip('"\'`')
            return keyword if keyword else None
        except Exception as e:
            logger.error(f"llm_keyword_extraction_failed label={entity_label} error={e}")
            return None
    
    def _search_event_api(self, search_keyword: str) -> List[Dict[str, Any]]:
        """
        调用事件API搜索
        
        Args:
            search_keyword: 搜索关键词
            
        Returns:
            事件候选列表
        """
        try:
            # 从 related_event_search 配置获取 API 相关参数
            api_config = self.config.get("api_config", {})
            api_url = api_config.get("url")
            api_key = api_config.get("key", "")
            limit = int(api_config.get("limit", 10))
            
            # 处理环境变量引用
            from ...utils.llm_api import _resolve_env
            api_key = _resolve_env(api_key)
            
            if not api_url or not api_key:
                logger.warning("related_event_search_api_missing_config")
                return []
            
            # 构建请求参数
            params = {
                "eventFreeText": search_keyword,
                "key": api_key,
                "pageSize": limit,
                "pageth": 1
            }
            
            # 发起HTTP请求
            import httpx
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }
            
            with httpx.Client(timeout=httpx.Timeout(15.0), headers=headers, follow_redirects=True) as client:
                resp = client.get(api_url, params=params)
                resp.raise_for_status()
                raw_result = resp.json()
            
            if not raw_result:
                return []
            
            # 使用独立的解析逻辑
            candidates = self._parse_event_api_response(raw_result)
            
            logger.info(f"event_api_search_result keyword={search_keyword} count={len(candidates)}")
            return candidates
            
        except Exception as e:
            logger.error(f"event_api_search_error keyword={search_keyword} error={e}")
            return []
    
    def _parse_event_api_response(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        解析事件API响应数据
        
        Args:
            raw_data: API原始响应
            
        Returns:
            解析后的事件候选列表
        """
        try:
            if not raw_data or not isinstance(raw_data, dict):
                return []
            
            data_list = raw_data.get("data", [])
            if not isinstance(data_list, list):
                return []
            
            # 从 related_event_search 配置获取字段映射
            api_config = self.config.get("api_config", {})
            fields_config = api_config.get("fields", {})
            fields_to_extract = fields_config.get("extract", ["title", "description", "begin", "end", "uri", "dateLabel"])
            field_mapping = fields_config.get("mapping", {})
            
            results = []
            for item in data_list:
                if not isinstance(item, dict):
                    continue
                
                parsed_item = {}
                
                # 提取并映射字段
                for field in fields_to_extract:
                    if field in item:
                        mapped_field = field_mapping.get(field, field)
                        value = item[field]
                        # 处理空值
                        if value is not None and str(value).strip():
                            parsed_item[mapped_field] = value
                        else:
                            parsed_item[mapped_field] = None
                
                # 添加原始数据以备后查
                parsed_item["_raw"] = item
                results.append(parsed_item)
            
            return results
            
        except Exception as e:
            logger.error(f"event_api_response_parse_error error={e}")
            return []
    
    def _filter_by_title(self, candidates: List[Dict[str, Any]], search_keyword: str) -> List[Dict[str, Any]]:
        """
        按title规则筛选候选事件
        
        Args:
            candidates: 候选事件列表
            search_keyword: 搜索关键词
            
        Returns:
            筛选后的候选列表
        """
        if not self.title_filter_required:
            return candidates
        
        # 将搜索关键词分割为多个词
        keywords = [kw.strip() for kw in search_keyword.split() if kw.strip()]
        if not keywords:
            return candidates
        
        filtered = []
        for candidate in candidates:
            title = candidate.get("label", "") or candidate.get("title", "")
            if not title:
                continue
            
            # 检查title是否包含任一关键词
            title_lower = title.lower()
            if any(kw.lower() in title_lower for kw in keywords):
                filtered.append(candidate)
        
        logger.info(f"title_filter_result keyword={search_keyword} original={len(candidates)} filtered={len(filtered)}")
        return filtered
    
    def _judge_event_relevance(
        self,
        entity_label: str,
        entity_type: str, 
        context_hint: str,
        search_keyword: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        使用大模型判断事件相关性
        
        Args:
            entity_label: 实体标签
            entity_type: 实体类型
            context_hint: 上下文提示
            search_keyword: 搜索关键词
            candidates: 候选事件列表
            
        Returns:
            按相关性排序的事件列表
        """
        if not candidates:
            return []
        
        try:
            # 构建提示词
            import os
            prompt_path = os.path.join("src", "prompts", "l2_event_relevance_judgment.md")
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    system_prompt = f.read()
            except Exception:
                system_prompt = """你是一个专业的事件相关性分析专家。请分析候选事件与目标实体的相关性，选出最相关的事件。

要求：
1. 分析实体与事件的关联度
2. 考虑时间、地点、人物等上下文因素
3. 按相关性排序，输出最相关的事件
4. 为每个事件提供置信度(0-1)和理由
"""
            
            # 构建候选事件描述
            candidates_text = "\n".join([
                f"{i+1}. 标题: {c.get('label', 'N/A')}\n"
                f"   描述: {c.get('description', 'N/A')}\n"
                f"   开始时间: {c.get('start_date', 'N/A')}\n"
                f"   结束时间: {c.get('end_date', 'N/A')}\n"
                f"   URI: {c.get('uri', 'N/A')}\n"
                for i, c in enumerate(candidates)
            ])
            
            user_content = f"""请分析以下候选事件与目标实体的相关性：

目标实体：
- 标签: {entity_label}
- 类型: {entity_type}  
- 搜索关键词: {search_keyword}
- 上下文: {context_hint}

候选事件：
{candidates_text}

请按JSON格式输出结果：
{{
  "relevant_events": [
    {{
      "uri": "事件URI",
      "label": "事件标题",
      "description": "事件描述",
      "confidence": 0.95,
      "reason": "相关性理由"
    }}
  ]
}}

请按相关性从高到低排序，只输出最相关的{self.max_events}个事件。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            output = invoke_model("l2_event_relevance_judgment", messages, self.settings)
            
            # 解析输出
            relevant_events = self._parse_relevance_output(output, candidates)
            logger.info(f"event_relevance_judgment_completed entity={entity_label} relevant_count={len(relevant_events)}")
            return relevant_events
            
        except Exception as e:
            logger.error(f"event_relevance_judgment_error entity={entity_label} error={e}")
            # 失败时返回前N个候选，设置低置信度
            return [
                {
                    "uri": c.get("uri"),
                    "label": c.get("label"),
                    "description": c.get("description"),
                    "confidence": 0.5,
                    "reason": "LLM判断失败，回退结果"
                }
                for c in candidates[:self.max_events]
            ]
    
    def _parse_relevance_output(self, output: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析大模型的相关性判断输出
        
        Args:
            output: LLM输出
            candidates: 原始候选列表
            
        Returns:
            解析后的相关事件列表
        """
        try:
            import json
            data = json.loads(output)
        except Exception:
            # 尝试JSON修复
            logger.info("attempting_relevance_json_repair")
            repaired_data = repair_json_output(output)
            if repaired_data:
                data = repaired_data
                logger.info("relevance_json_repair_success")
            else:
                logger.warning("relevance_json_parse_failed")
                return []
        
        relevant_events = data.get("relevant_events", [])
        if not isinstance(relevant_events, list):
            return []
        
        # 构建URI到候选的映射，用于补充信息
        uri_to_candidate = {c.get("uri"): c for c in candidates if c.get("uri")}
        
        result = []
        for event in relevant_events:
            if not isinstance(event, dict):
                continue
            
            uri = event.get("uri")
            confidence = event.get("confidence", 0.0)
            
            # 置信度阈值过滤
            if confidence < self.min_confidence:
                continue
            
            # 从原始候选中补充完整信息
            candidate = uri_to_candidate.get(uri, {})
            
            result.append({
                "uri": uri,
                "label": event.get("label") or candidate.get("label"),
                "description": event.get("description") or candidate.get("description"),
                "confidence": confidence,
                "reason": event.get("reason", ""),
                # 补充额外属性
                "start_date": candidate.get("start_date"),
                "end_date": candidate.get("end_date"),
                "date_label": candidate.get("date_label")
            })
        
        return result[:self.max_events]
    
    def _get_model_name(self) -> str:
        """获取当前使用的模型名称"""
        try:
            # 从事件关键词提取任务配置获取模型名
            task_config = self.settings.get("tasks", {}).get("l2_event_keyword_extraction", {})
            if not task_config:
                task_config = self.settings.get("tasks", {}).get("l2_disambiguation", {})
            
            provider_type = task_config.get("provider_type", "text")
            provider_config = self.settings.get("api_providers", {}).get(provider_type, {})
            return provider_config.get("primary", {}).get("model", "unknown")
        except Exception:
            return "unknown"
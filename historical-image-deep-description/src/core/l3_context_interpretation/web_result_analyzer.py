"""
Web搜索结果分析器

实现两阶段分析流程：
1. 第一阶段：信息甄别与评估 - 对每条搜索结果进行相关性评分
2. 第二阶段：深度阐释与生成 - 基于高分结果生成历史文化阐释
"""

import os
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ...utils.logger import get_logger
from ...utils.llm_api import invoke_model
from .zhipu_client import ZhipuSearchResponse

logger = get_logger(__name__)


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    success: bool
    content: str
    model_name: str
    error: Optional[str] = None


@dataclass
class AssessmentResult:
    """第一阶段评估结果数据类"""
    refer: str
    score: int
    reason: str


@dataclass
class StageOneResult:
    """第一阶段完整结果"""
    success: bool
    assessments: List[AssessmentResult]
    model_name: str
    error: Optional[str] = None


class WebResultAnalyzer:
    """
    Web搜索结果分析器
    
    实现两阶段分析流程：
    1. 第一阶段：信息甄别与评估 - 对每条搜索结果进行相关性评分
    2. 第二阶段：深度阐释与生成 - 基于高分结果生成历史文化阐释
    """
    
    def __init__(self, settings: Dict[str, Any]):
        """
        初始化分析器
        
        Args:
            settings: 全局配置字典
        """
        self.settings = settings
        self.web_config = self._get_web_search_config()
        self.llm_config = self._get_llm_config()
        
        # 加载两个阶段的系统提示词
        self.stage_one_prompt = self._load_system_prompt("l3_web_search_analysis.md")
        self.stage_two_prompt = self._load_system_prompt("l3_web_search_report.md")
        
        # 两阶段的配置
        self.assessment_config = self.web_config.get("assessment", {})
        self.report_config = self.web_config.get("report", {})
        
        logger.info("Web结果分析器初始化完成（两阶段模式）")
    
    def _get_web_search_config(self) -> Dict[str, Any]:
        """获取Web搜索配置"""
        return self.settings.get("l3_context_interpretation", {}).get("web_search", {})
    
    def _get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        llm_analysis_config = self.web_config.get("llm_analysis", {})
        
        # 从新的tasks配置获取两个阶段的配置
        stage_one_config = self.settings.get("tasks", {}).get("l3_web_search_stage_one", {})
        stage_two_config = self.settings.get("tasks", {}).get("l3_web_search_stage_two", {})
        
        # 获取provider_type（两个阶段应该使用相同的provider）
        provider_type = stage_one_config.get("provider_type", "text")
        
        # 根据内存规范，通过settings["api_providers"]路径获取模型名称
        try:
            model_name = self.settings["api_providers"][provider_type]["primary"]["model"]
        except KeyError:
            logger.warning(f"无法从api_providers获取模型名称，使用默认值")
            model_name = "gpt-4"
        
        return {
            "provider": provider_type,
            "model": model_name,
            "max_tokens": llm_analysis_config.get("max_tokens", 2000),
            "stage_one_temperature": stage_one_config.get("temperature", 0.1),
            "stage_two_temperature": stage_two_config.get("temperature", 0.3)
        }

    def _load_system_prompt(self, filename: str) -> str:
        """
        加载系统提示词
        
        Args:
            filename: 提示词文件名
            
        Returns:
            str: 提示词内容
        """
        try:
            prompt_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "..", "prompts", 
                filename
            )
            
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
                
        except Exception as e:
            logger.error(f"加载系统提示词失败 filename={filename}: {e}")
            return "你是一位历史文化研究助手。"

    def analyze_search_results(
        self, 
        entity: Dict[str, Any], 
        search_response: ZhipuSearchResponse
    ) -> AnalysisResult:
        """
        两阶段分析搜索结果
        
        第一阶段：信息甄别与评估 - 对每条搜索结果进行相关性评分
        第二阶段：深度阐释与生成 - 基于高分结果生成历史文化阐释
        
        Args:
            entity: 实体信息字典
            search_response: 智谱AI搜索响应
            
        Returns:
            AnalysisResult: 分析结果
        """
        try:
            # 第一阶段：信息甄别与评估
            stage_one_result = self._stage_one_assessment(entity, search_response)
            
            if not stage_one_result.success:
                logger.error(f"第一阶段处理失败 label='{entity.get('label', '')}' error={stage_one_result.error}")
                return AnalysisResult(
                    success=False,
                    content="",
                    model_name=stage_one_result.model_name,
                    error=f"第一阶段失败: {stage_one_result.error}"
                )
            
            # 筛选高分结果
            high_score_results = self._filter_high_score_results(stage_one_result.assessments, search_response)
            
            if not high_score_results:
                logger.info(f"无高相关性结果 label='{entity.get('label', '')}' 筛选后结果为空")
                return AnalysisResult(
                    success=True,
                    content="经评估，搜索结果中未找到高相关性的信息。",
                    model_name=stage_one_result.model_name
                )
            
            # 第二阶段：深度阐释与生成
            stage_two_result = self._stage_two_report_generation(entity, high_score_results)
            
            if stage_two_result.success:
                logger.info(f"两阶段分析成功 label='{entity.get('label', '')}' content_len={len(stage_two_result.content)}")
                return stage_two_result
            else:
                logger.error(f"第二阶段处理失败 label='{entity.get('label', '')}' error={stage_two_result.error}")
                return AnalysisResult(
                    success=False,
                    content="",
                    model_name=stage_two_result.model_name,
                    error=f"第二阶段失败: {stage_two_result.error}"
                )
                
        except Exception as e:
            error_msg = f"两阶段分析过程异常: {str(e)}"
            logger.error(f"Web结果分析异常 label='{entity.get('label', '')}' error={error_msg}")
            return AnalysisResult(
                success=False,
                content="",
                model_name=self.llm_config["model"],
                error=error_msg
            )
    
    def _stage_one_assessment(
        self,
        entity: Dict[str, Any],
        search_response: ZhipuSearchResponse
    ) -> StageOneResult:
        """
        第一阶段：信息甄别与评估
        
        对每条搜索结果进行相关性评分（0-10分）
        
        Args:
            entity: 实体信息字典
            search_response: 搜索响应
        
        Returns:
            StageOneResult: 第一阶段结果
        """
        try:
            # 构建第一阶段的用户提示词
            user_prompt = self._build_stage_one_prompt(entity, search_response)
            
            logger.info(f"开始第一阶段评估 label='{entity.get('label', '')}' model={self.llm_config['model']}")
            
            # 调用LLM API
            messages = [
                {"role": "system", "content": self.stage_one_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            content = invoke_model(
                task_name="l3_web_search_stage_one",
                messages=messages,
                settings=self.settings,
                provider_type=self.llm_config["provider"],
                temperature=self.llm_config["stage_one_temperature"]
            )
            
            if not content or not content.strip():
                return StageOneResult(
                    success=False,
                    assessments=[],
                    model_name=self.llm_config["model"],
                    error="LLM返回空内容"
                )
            
            # 解析JSON结果
            assessments = self._parse_stage_one_response(content)
            
            if not assessments:
                return StageOneResult(
                    success=False,
                    assessments=[],
                    model_name=self.llm_config["model"],
                    error="无法解析评估结果"
                )
            
            # 获取实际使用的模型名称
            try:
                provider_type = self.llm_config["provider"]
                model_name = self.settings["api_providers"][provider_type]["primary"]["model"]
            except (KeyError, TypeError):
                model_name = self.llm_config["model"]
            
            logger.info(f"第一阶段评估成功 label='{entity.get('label', '')}' assessments_count={len(assessments)}")
            return StageOneResult(
                success=True,
                assessments=assessments,
                model_name=model_name
            )
            
        except Exception as e:
            error_msg = f"第一阶段评估异常: {str(e)}"
            logger.error(f"第一阶段处理失败 label='{entity.get('label', '')}' error={error_msg}")
            return StageOneResult(
                success=False,
                assessments=[],
                model_name=self.llm_config["model"],
                error=error_msg
            )

    def _build_stage_one_prompt(
        self,
        entity: Dict[str, Any],
        search_response: ZhipuSearchResponse
    ) -> str:
        """
        构建第一阶段的用户提示词
        
        Args:
            entity: 实体信息
            search_response: 搜索响应
            
        Returns:
            str: 用户提示词
        """
        # 获取实体基本信息
        label = entity.get("label", "")
        entity_type = entity.get("type", "")
        
        # 获取初始元数据（根据规范，直接从实体节点获取）
        context_hint = entity.get("context_hint", "")
        
        # 格式化搜索结果为 JSON 格式（模拟智谱AI返回格式）
        search_results_json = self._format_search_results_as_json(search_response)
        
        # 构建完整提示词
        prompt_parts = [
            f"# 实体信息",
            f"- **label**: {label}",
            f"- **type**: {entity_type}",
            "",
            f"# 初始元数据",
            context_hint if context_hint else "（无初始元数据）",
            "",
            f"# 网络搜索结果",
            search_results_json
        ]
        
        return "\n".join(prompt_parts)
    
    def _format_search_results_as_json(self, search_response: ZhipuSearchResponse) -> str:
        """
        将搜索结果格式化为 JSON 格式（模拟智谱 AI 返回）
        
        Args:
            search_response: 搜索响应
            
        Returns:
            str: JSON 格式的搜索结果
        """
        if not search_response.success:
            return json.dumps({"error": search_response.error}, ensure_ascii=False, indent=2)
        
        if not search_response.results:
            return json.dumps({"message": "未找到相关搜索结果"}, ensure_ascii=False, indent=2)
        
        # 构建类似智谱 AI 的 JSON 格式
        search_results_data = {
            "created": 1748261757,  # 模拟时间戳
            "id": f"search_{hash(search_response.query) % 1000000}",
            "request_id": f"search_{hash(search_response.query) % 1000000}",
            "search_intent": [
                {
                    "intent": "SEARCH_ALL",
                    "keywords": search_response.query,
                    "query": f"搜索{search_response.query}的相关信息"
                }
            ],
            "search_result": []
        }
        
        # 添加搜索结果
        for i, result in enumerate(search_response.results[:15], 1):  # 限制前15个结果
            formatted_result = {
                "content": result.get("content", "")[:500],  # 限制内容长度
                "icon": "https://example.com/icon.jpg",  # 模拟图标
                "link": result.get("url", ""),
                "media": result.get("source", "未知来源"),
                "publish_date": "2025-01-01",  # 模拟发布日期
                "refer": f"ref_{i}",
                "title": result.get("title", "无标题")
            }
            search_results_data["search_result"].append(formatted_result)
        
        return json.dumps(search_results_data, ensure_ascii=False, indent=2)

    def _parse_stage_one_response(self, content: str) -> List[AssessmentResult]:
        """
        解析第一阶段LLM的JSON响应
        
        Args:
            content: LLM返回的JSON字符串
            
        Returns:
            List[AssessmentResult]: 评估结果列表
        """
        try:
            # 提取JSON代码块
            json_str = self._extract_json_from_content(content)
            if not json_str:
                logger.error("无法从响应中提取JSON内容")
                return []
            
            # 解析JSON
            data = json.loads(json_str)
            
            # 提取assessment_results
            assessment_results = data.get("assessment_results", [])
            
            assessments = []
            for item in assessment_results:
                try:
                    assessment = AssessmentResult(
                        refer=item["refer"],
                        score=int(item["score"]),
                        reason=item["reason"]
                    )
                    assessments.append(assessment)
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"跳过无效的评估项: {item}, error: {e}")
                    continue
            
            return assessments
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, content: {content[:200]}...")
            return []
        except Exception as e:
            logger.error(f"解析第一阶段响应异常: {e}")
            return []
    
    def _extract_json_from_content(self, content: str) -> Optional[str]:
        """
        从LLM响应中提取JSON内容
        
        Args:
            content: LLM响应内容
            
        Returns:
            Optional[str]: 提取的JSON字符串，如果没有找到则返回None
        """
        import re
        
        # 尝试提取```json代码块
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        # 如果没有代码块，尝试直接查找JSON对象
        json_object_pattern = r'\{[^{}]*"assessment_results"[^}]*\}'
        match = re.search(json_object_pattern, content, re.DOTALL)
        
        if match:
            return match.group(0).strip()
        
        # 最后尝试找到任何包含assessment_results的JSON结构
        lines = content.split('\n')
        json_lines = []
        in_json = False
        brace_count = 0
        
        for line in lines:
            if '{' in line and not in_json:
                in_json = True
                brace_count = line.count('{') - line.count('}')
                json_lines.append(line)
            elif in_json:
                json_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                if brace_count == 0:
                    break
        
        if json_lines:
            potential_json = '\n'.join(json_lines)
            if 'assessment_results' in potential_json:
                return potential_json
        
        return None

    def _filter_high_score_results(
        self, 
        assessments: List[AssessmentResult], 
        search_response: ZhipuSearchResponse
    ) -> List[Dict[str, Any]]:
        """
        筛选高分搜索结果
        
        Args:
            assessments: 第一阶段评估结果
            search_response: 原始搜索响应
            
        Returns:
            List[Dict[str, Any]]: 高分搜索结果列表
        """
        # 从配置获取分数阈值，默认为8分
        score_threshold = self.assessment_config.get("score_threshold", 8)
        
        # 建立refer到评分的映射
        refer_to_score = {assessment.refer: assessment.score for assessment in assessments}
        
        # 建立refer到搜索结果的映射
        refer_to_result = {}
        for i, result in enumerate(search_response.results, 1):
            refer = f"ref_{i}"
            refer_to_result[refer] = result
        
        # 筛选高分结果
        high_score_results = []
        for assessment in assessments:
            if assessment.score >= score_threshold and assessment.refer in refer_to_result:
                result_data = refer_to_result[assessment.refer].copy()
                result_data["assessment_score"] = assessment.score
                result_data["assessment_reason"] = assessment.reason
                result_data["refer"] = assessment.refer
                high_score_results.append(result_data)
        
        # 按分数排序（高分在前）
        high_score_results.sort(key=lambda x: x["assessment_score"], reverse=True)
        
        # 限制最大数量
        max_results = self.assessment_config.get("max_selected_results", 3)
        high_score_results = high_score_results[:max_results]
        
        logger.info(f"筛选出高分结果 threshold={score_threshold} selected_count={len(high_score_results)}")
        return high_score_results

    def _stage_two_report_generation(
        self,
        entity: Dict[str, Any],
        high_score_results: List[Dict[str, Any]]
    ) -> AnalysisResult:
        """
        第二阶段：深度阐释与生成
        
        基于高分搜索结果生成历史文化价值阐释
        
        Args:
            entity: 实体信息字典
            high_score_results: 高分搜索结果列表
            
        Returns:
            AnalysisResult: 分析结果
        """
        try:
            # 构建第二阶段的用户提示词
            user_prompt = self._build_stage_two_prompt(entity, high_score_results)
            
            logger.info(f"开始第二阶段报告生成 label='{entity.get('label', '')}' high_score_count={len(high_score_results)}")
            
            # 调用LLM API
            messages = [
                {"role": "system", "content": self.stage_two_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            content = invoke_model(
                task_name="l3_web_search_stage_two",
                messages=messages,
                settings=self.settings,
                provider_type=self.llm_config["provider"],
                temperature=self.llm_config["stage_two_temperature"]
            )
            
            if not content or not content.strip():
                return AnalysisResult(
                    success=False,
                    content="",
                    model_name=self.llm_config["model"],
                    error="LLM返回空内容"
                )
            
            # 获取实际使用的模型名称
            try:
                provider_type = self.llm_config["provider"]
                model_name = self.settings["api_providers"][provider_type]["primary"]["model"]
            except (KeyError, TypeError):
                model_name = self.llm_config["model"]
            
            logger.info(f"第二阶段报告生成成功 label='{entity.get('label', '')}' content_len={len(content)}")
            return AnalysisResult(
                success=True,
                content=content.strip(),
                model_name=model_name
            )
            
        except Exception as e:
            error_msg = f"第二阶段报告生成异常: {str(e)}"
            logger.error(f"第二阶段处理失败 label='{entity.get('label', '')}' error={error_msg}")
            return AnalysisResult(
                success=False,
                content="",
                model_name=self.llm_config["model"],
                error=error_msg
            )

    def _build_stage_two_prompt(
        self,
        entity: Dict[str, Any],
        high_score_results: List[Dict[str, Any]]
    ) -> str:
        """
        构建第二阶段的用户提示词
        
        Args:
            entity: 实体信息
            high_score_results: 高分搜索结果列表
            
        Returns:
            str: 用户提示词
        """
        # 获取实体基本信息
        label = entity.get("label", "")
        entity_type = entity.get("type", "")
        
        # 获取初始元数据
        context_hint = entity.get("context_hint", "")
        
        # 格式化高分搜索结果
        selected_results_json = self._format_selected_results_as_json(high_score_results)
        
        # 构建完整提示词
        prompt_parts = [
            f"# 实体信息",
            f"- **label**: {label}",
            f"- **type**: {entity_type}",
            "",
            f"# 初始元数据",
            context_hint if context_hint else "（无初始元数据）",
            "",
            f"# 精选网络搜索结果",
            "以下是经过第一阶段评估筛选出的高相关性搜索结果：",
            "",
            selected_results_json
        ]
        
        return "\n".join(prompt_parts)

    def _format_selected_results_as_json(self, high_score_results: List[Dict[str, Any]]) -> str:
        """
        将筛选后的高分结果格式化为JSON
        
        Args:
            high_score_results: 高分搜索结果列表
            
        Returns:
            str: JSON格式的筛选结果
        """
        selected_data = []
        
        for result in high_score_results:
            selected_item = {
                "refer": result.get("refer", ""),
                "title": result.get("title", "无标题"),
                "content": result.get("content", ""),
                "url": result.get("url", ""),
                "source": result.get("source", "未知来源"),
                "assessment_score": result.get("assessment_score", 0),
                "assessment_reason": result.get("assessment_reason", "")
            }
            selected_data.append(selected_item)
        
        return json.dumps(selected_data, ensure_ascii=False, indent=2)
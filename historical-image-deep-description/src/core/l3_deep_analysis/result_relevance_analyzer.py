# -*- coding: utf-8 -*-
"""
Deep Analysis 结果相关性分析器

功能：
1. 对 GLM/Dify 返回的单条结果进行相关性评分（0-10分）
2. 根据阈值判断是否相关，低于阈值则标记为 not_relevant
3. 更新结果元数据，添加 assessment 字段
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from ...utils.logger import get_logger
from ...utils.llm_api import invoke_model

logger = get_logger(__name__)


@dataclass
class RelevanceAssessment:
    """相关性评估结果"""
    score: int
    reason: str
    assessor_model: str
    assessed_at: str


class ResultRelevanceAnalyzer:
    """
    结果相关性分析器

    对 GLM/Dify 检索返回的单条结果进行相关性评估，复用 L3 Web Search 的评分机制。
    """

    def __init__(self, settings: Dict[str, Any]):
        """
        初始化分析器

        Args:
            settings: 全局配置字典
        """
        self.settings = settings
        self.config = settings.get("deep_analysis", {}).get("relevance_assessment", {})
        self.glm_config = self.config.get("glm", {})
        self.dify_config = self.config.get("dify", {})

        # 加载系统提示词（复用 l3_web_search_analysis.md）
        self.system_prompt = self._load_system_prompt("l3_web_search_analysis.md")

        logger.info("结果相关性分析器初始化完成")

    def is_enabled(self, executor_type: str) -> bool:
        """
        检查指定执行器的相关性评估是否启用

        Args:
            executor_type: 执行器类型，"glm" 或 "dify"

        Returns:
            bool: 是否启用
        """
        if not self.config.get("enabled", True):
            return False

        executor_config = self.config.get(executor_type, {})
        return executor_config.get("enabled", True)

    def get_threshold(self, executor_type: str) -> int:
        """
        获取指定执行器的相关性阈值

        Args:
            executor_type: 执行器类型，"glm" 或 "dify"

        Returns:
            int: 阈值分数（0-10）
        """
        executor_config = self.config.get(executor_type, {})
        return executor_config.get("score_threshold", 6)

    def get_task_name(self, executor_type: str) -> str:
        """
        获取指定执行器的 LLM 任务名称

        Args:
            executor_type: 执行器类型，"glm" 或 "dify"

        Returns:
            str: 任务名称
        """
        executor_config = self.config.get(executor_type, {})
        return executor_config.get("llm_task_name", f"deep_{executor_type}_relevance")

    def assess_result(
        self,
        question: str,
        content: str,
        subtopic_name: str,
        executor_type: str = "glm"
    ) -> Optional[RelevanceAssessment]:
        """
        评估 GLM/Dify 结果的相关性

        Args:
            question: 检索问题
            content: 返回的内容
            subtopic_name: 子主题名称
            executor_type: 执行器类型，"glm" 或 "dify"

        Returns:
            RelevanceAssessment or None（如果未启用或评估失败）
        """
        if not self.is_enabled(executor_type):
            logger.debug(f"相关性评估未启用 executor_type={executor_type}")
            return None

        # 检查是否需要跳过已评估的结果
        reassess_if_exists = self.config.get("reassess_if_exists", False)
        if not reassess_if_exists:
            # 这个检查在调用方完成，这里不做判断
            pass

        try:
            # 构建用户提示词
            user_prompt = self._build_assessment_prompt(
                question=question,
                content=content,
                subtopic_name=subtopic_name,
                executor_type=executor_type
            )

            logger.info(f"开始相关性评估 executor_type={executor_type} question_preview={question[:50]}")

            # 调用 LLM
            task_name = self.get_task_name(executor_type)
            response = invoke_model(
                task_name=task_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                settings=self.settings,
                provider_type=self.settings.get("tasks", {}).get(task_name, {}).get("provider_type", "text-small"),
                temperature=0.1
            )

            if not response or not response.strip():
                logger.error(f"相关性评估失败 executor_type={executor_type} error=LLM返回空内容")
                return None

            # 解析 JSON 响应
            assessment = self._parse_assessment_response(response)

            if assessment:
                logger.info(f"相关性评估成功 executor_type={executor_type} score={assessment.score}")
            else:
                logger.warning(f"相关性评估解析失败 executor_type={executor_type}")

            return assessment

        except Exception as e:
            logger.error(f"相关性评估异常 executor_type={executor_type} error={str(e)}")
            return None

    def update_result_meta(
        self,
        result: Dict[str, Any],
        assessment: Optional[RelevanceAssessment],
        threshold: int
    ) -> Dict[str, Any]:
        """
        更新结果的 meta 信息

        如果 assessment.score < threshold，则将 meta.status 改为 "not_relevant"

        Args:
            result: 原始结果字典 {content, meta}
            assessment: 评估结果
            threshold: 阈值分数

        Returns:
            Dict[str, Any]: 更新后的结果字典
        """
        if assessment is None:
            return result

        meta = result.get("meta", {})

        # 添加 assessment 信息
        meta["assessment"] = {
            "score": assessment.score,
            "reason": assessment.reason,
            "assessed_at": assessment.assessed_at,
            "assessor_model": assessment.assessor_model
        }

        # 根据阈值调整 status
        original_status = meta.get("status", "")
        if assessment.score < threshold and original_status == "success":
            meta["status"] = "not_relevant"
            meta["original_status"] = original_status
            logger.info(f"结果标记为不相关 score={assessment.score} threshold={threshold} original_status={original_status}")

        result["meta"] = meta
        return result

    def should_skip_assessment(self, existing_meta: Dict[str, Any], executor_type: str) -> bool:
        """
        判断是否应该跳过评估（幂等性检查）

        Args:
            existing_meta: 现有的 meta 字典
            executor_type: 执行器类型

        Returns:
            bool: 是否跳过
        """
        reassess_if_exists = self.config.get("reassess_if_exists", False)
        if reassess_if_exists:
            return False

        existing_assessment = existing_meta.get("assessment")
        if existing_assessment:
            logger.debug(f"跳过已评估的结果 executor_type={executor_type}")
            return True

        return False

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
            return "你是一位资料评估专家，请对检索结果的相关性进行评分（0-10分）。"

    def _build_assessment_prompt(
        self,
        question: str,
        content: str,
        subtopic_name: str,
        executor_type: str
    ) -> str:
        """
        构建评估提示词

        适配单结果场景，构建类似多结果的 JSON 格式以复用现有提示词

        Args:
            question: 检索问题
            content: 返回内容
            subtopic_name: 子主题名称
            executor_type: 执行器类型

        Returns:
            str: 用户提示词
        """
        # 限制内容长度，避免 token 过大
        max_content_length = 2000
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "...[内容已截断]"

        # 构建模拟的多结果 JSON（复用 l3_web_search_analysis.md 的格式）
        # 将问题作为 label，内容作为搜索结果
        fake_search_result = {
            "created": 1748261757,
            "id": f"search_{hash(question) % 1000000}",
            "request_id": f"deep_{executor_type}_{hash(question) % 1000000}",
            "search_intent": [
                {
                    "intent": "DEEP_ANALYSIS",
                    "keywords": question,
                    "query": f"深度分析：{question}"
                }
            ],
            "search_result": [
                {
                    "content": truncated_content,
                    "icon": "",
                    "link": "",
                    "media": f"{executor_type.upper()}_ASSISTANT",
                    "publish_date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
                    "refer": "ref_1",
                    "title": question[:100]  # 使用问题作为标题
                }
            ]
        }

        # 构建完整提示词（符合 l3_web_search_analysis.md 的输入格式）
        prompt_parts = [
            "# 实体信息",
            f"- **label**: {question}",
            f"- **type**: {subtopic_name or '深度分析'}",
            "",
            "# 初始元数据",
            f"任务类型：深度分析\\n子主题：{subtopic_name}\\n检索问题：{question}",
            "",
            "# 网络搜索结果",
            json.dumps(fake_search_result, ensure_ascii=False, indent=2)
        ]

        return "\\n".join(prompt_parts)

    def _parse_assessment_response(self, response: str) -> Optional[RelevanceAssessment]:
        """
        解析 LLM 返回的 JSON

        Args:
            response: LLM 返回的 JSON 字符串

        Returns:
            RelevanceAssessment or None
        """
        try:
            # 提取 JSON 代码块
            json_str = self._extract_json_from_content(response)
            if not json_str:
                logger.error("无法从响应中提取 JSON 内容")
                return None

            # 解析 JSON
            data = json.loads(json_str)

            # 提取 assessment_results（复用 l3_web_search_analysis.md 的格式）
            assessment_results = data.get("assessment_results", [])

            if not assessment_results:
                logger.error("JSON 中未找到 assessment_results 字段")
                return None

            # 取第一条结果（因为我们只传入了一条结果）
            first_result = assessment_results[0]

            score = int(first_result.get("score", 0))
            reason = first_result.get("reason", "")

            # 获取模型名称
            task_name = "deep_relevance"
            try:
                provider_type = self.settings.get("tasks", {}).get(task_name, {}).get("provider_type", "text-small")
                model_name = self.settings["api_providers"][provider_type]["primary"]["model"]
            except (KeyError, TypeError):
                model_name = "unknown"

            assessed_at = datetime.now(timezone(timedelta(hours=8))).isoformat()

            return RelevanceAssessment(
                score=score,
                reason=reason,
                assessor_model=model_name,
                assessed_at=assessed_at
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}, response: {response[:200]}...")
            return None
        except Exception as e:
            logger.error(f"解析评估响应异常: {e}")
            return None

    def _extract_json_from_content(self, content: str) -> Optional[str]:
        """
        从 LLM 响应中提取 JSON 内容

        Args:
            content: LLM 响应内容

        Returns:
            Optional[str]: 提取的 JSON 字符串
        """
        import re

        # 尝试提取 ```json 代码块
        json_pattern = r'```(?:json)?\\s*(\\{.*?\\})\\s*```'
        match = re.search(json_pattern, content, re.DOTALL | re.IGNORECASE)

        if match:
            return match.group(1).strip()

        # 如果没有代码块，尝试直接查找包含 assessment_results 的 JSON 对象
        json_object_pattern = r'\\{[^{}]*"assessment_results"[^}]*\\}'
        match = re.search(json_object_pattern, content, re.DOTALL)

        if match:
            return match.group(0).strip()

        # 最后尝试找到任何包含 assessment_results 的 JSON 结构
        lines = content.split('\\n')
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
            potential_json = '\\n'.join(json_lines)
            if 'assessment_results' in potential_json:
                return potential_json

        return None

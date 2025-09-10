#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel公式生成器 - 后端（优化版）
职责：
1. 接收【已增强】的 requirement（含数据结构信息）
2. 只做兜底补全，不再重复拼接
3. 调用 LLM 并返回结果
"""

import os
import json
import re
import threading
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from modules.config_manager import ConfigManager
from modules.prompt_manager import PromptManager
from units.llm_client import LLMClient


class RequirementProcessor:
    """需求描述处理器 - 优化后仅做兜底"""
    def validate_requirement(self, text: str):
        if not text or not text.strip():
            return False, "请描述您的处理需求"
        return True, "验证通过"

    def build_context_for_ai(self, requirement: str, columns: List[str], sample_data: str) -> str:
        # 前端已增强，直接返回
        return requirement

class FormulaCache:
    """LRU 缓存 - 无改动"""
    def __init__(self, max_size: int = 50):
        self.cache, self.access_times, self.max_size = {}, {}, max_size

    def get_cached_formula(self, requirement: str, columns: List[str]) -> Optional[Dict[str, Any]]:
        key = f"{requirement.strip()}|{','.join(sorted(columns))}"
        if key in self.cache:
            self.access_times[key] = datetime.now()
            return self.cache[key].copy()
        return None

    def cache_formula(self, requirement: str, columns: List[str], result: Dict[str, Any]) -> None:
        key = f"{requirement.strip()}|{','.join(sorted(columns))}"
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            self.cache.pop(oldest, None)
            self.access_times.pop(oldest, None)
        self.cache[key], self.access_times[key] = result.copy(), datetime.now()

    def clear_cache(self):
        self.cache.clear(); self.access_times.clear()


class FormulaHistory:
    """历史记录 - 无改动"""
    def __init__(self, max_history: int = 20):
        self.history, self.max_history = [], max_history

    def add_formula(self, requirement: str, formula: str, explanation: str, columns: List[str]) -> None:
        self.history.insert(0, dict(
            id=str(uuid.uuid4())[:8], timestamp=datetime.now(),
            requirement=requirement, formula=formula,
            explanation=explanation, columns=columns.copy(), success=True))
        self.history = self.history[:self.max_history]

    def get_recent_formulas(self, limit: int = 5) -> List[Dict[str, Any]]:
        return [r.copy() for r in self.history[:limit]]

    def clear_history(self): self.history.clear()


class OptimizedFormulaGenerator:
    """公式生成入口 - 只留核心逻辑"""
    def __init__(self):
        self.config_manager = ConfigManager()
        self.prompt_manager = PromptManager()
        self.llm_client = LLMClient(self.config_manager)
        self.requirement_processor = RequirementProcessor()
        self.cache = FormulaCache()
        self.history = FormulaHistory()
        self._ensure_default_prompts()

    # ------------------- 默认提示词 -------------------
    def _ensure_default_prompts(self):
        try:
            if not any(p.get('id') == 'formula_generation_system' for p in self.prompt_manager.get_all_prompts()):
                self._load_default_prompts_from_config()
        except Exception as e:
            print(f"加载默认提示词失败: {e}")

    def _load_default_prompts_from_config(self):
        path = os.path.join("config", "default_prompts.json")
        if not os.path.exists(path): return
        with open(path, encoding='utf-8') as f:
            defaults = json.load(f)
        if 'formula_generation_system' in defaults:
            self.prompt_manager.save_prompt(defaults['formula_generation_system'])

    # ------------------- 唯一入口 -------------------
    def generate_formula(self, requirement: str, columns: List[str],
                         sample_data: str = "", progress_callback: Optional[Callable] = None,
                         selected_prompt: str = "", selected_model: str = "",
                         temperature: float = 0.1, top_p: float = 0.9) -> Dict[str, Any]:
        try:
            if progress_callback: progress_callback("验证输入...")
            ok, msg = self.requirement_processor.validate_requirement(requirement)
            if not ok:
                return dict(formula='', explanation='', success=False, error=msg, from_cache=False)

            if progress_callback: progress_callback("检查缓存...")
            cached = self.cache.get_cached_formula(requirement, columns)
            if cached:
                cached['from_cache'] = True
                return cached

            if progress_callback: progress_callback("调用AI...")
            ai_result = self._call_ai(requirement, columns, sample_data,
                                      selected_prompt, selected_model, temperature, top_p)
            if ai_result['success']:
                self.cache.cache_formula(requirement, columns, ai_result)
                self.history.add_formula(requirement, ai_result['formula'],
                                         ai_result['explanation'], columns)
            if progress_callback: progress_callback("生成完成")
            return ai_result
        except Exception as e:
            return dict(formula='', explanation='', success=False, error=f'生成公式时出错：{e}', from_cache=False)

    # ------------------- 内部 -------------------
    def _call_ai(self, requirement: str, columns: List[str], sample_data: str,
                 selected_prompt: str, selected_model: str, temperature: float, top_p: float):
        system = self._get_system_prompt(selected_prompt)
        user = self.requirement_processor.build_context_for_ai(requirement, columns, sample_data)
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user}]
        model_config = None
        if selected_model:
            for m in self.config_manager.get_all_models():
                if m.get('name') == selected_model or m.get('model_id') == selected_model:
                    model_config = m
                    break
        response = self.llm_client.chat_completion(messages=messages,
                                                   temperature=temperature,
                                                   top_p=top_p,
                                                   model_config=model_config)
        return dict(formula='', explanation=response.strip() if response else '',
                    success=True, error='', from_cache=False)

    def _get_system_prompt(self, selected: str) -> str:
        if selected:
            for p in self.prompt_manager.get_all_prompts():
                if p.get('name') == selected or p.get('id') == selected:
                    return p.get('content', '')
        for p in self.prompt_manager.get_all_prompts():
            if p.get('id') == 'formula_generation_system':
                return p.get('content', '')
        return self._fallback_prompt()

    def _fallback_prompt(self) -> str:
        path = os.path.join("config", "default_prompts.json")
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                d = json.load(f).get('formula_generation_fallback', {})
                return d.get('content', '')
        return "请根据用户需求生成Excel公式，格式：公式：=你的公式\\n说明：公式说明"

    # ------------------- 异步包裹 -------------------
    def generate_formula_async(self, requirement: str, columns: List[str],
                               sample_data: str = "", selected_prompt: str = "",
                               selected_model: str = "", temperature: float = 0.1, top_p: float = 0.9,
                               success_callback: Optional[Callable] = None,
                               error_callback: Optional[Callable] = None,
                               progress_callback: Optional[Callable] = None):
        def run():
            try:
                res = self.generate_formula(requirement, columns, sample_data,
                                            progress_callback, selected_prompt,
                                            selected_model, temperature, top_p)
                (success_callback if res['success'] else error_callback)(res)
            except Exception as e:
                if error_callback:
                    error_callback(dict(formula='', explanation='', success=False,
                                        error=f'异步生成失败：{e}', from_cache=False))
        threading.Thread(target=run, daemon=True).start()

    # ------------------- 统计 -------------------
    def get_cache_statistics(self): return dict(cache_size=len(self.cache.cache),
                                                max_cache_size=self.cache.max_size,
                                                cache_hit_available=len(self.cache.cache) > 0)
    def get_history_statistics(self): return dict(total_formulas=len(self.history.history),
                                                 max_history_size=self.history.max_history,
                                                 recent_formulas=self.history.get_recent_formulas(3))
    def clear_cache(self): self.cache.clear_cache()
    def clear_history(self): self.history.clear_history()
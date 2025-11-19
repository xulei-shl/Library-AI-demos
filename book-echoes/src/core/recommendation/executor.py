import json
from typing import Any, Dict, List

from src.utils.logger import get_logger
from src.utils.llm.exceptions import JSONParseError

from .prompt_builder import build_initial_prompt, build_final_prompt, build_runoff_prompt, build_semifinal_prompt
from .config import recommend_quota

logger = get_logger(__name__)


def _safe_parse_json(text: str) -> Dict[str, Any]:
    """Parse a JSON string returned by the LLM, raising on invalid content."""
    s = (text or "").strip()
    if not s:
        raise JSONParseError(text, "LLM返回为空响应")
    fence_start = s.find("```")
    if fence_start != -1:
        fence_end = s.rfind("```")
        if fence_end > fence_start:
            s = s[fence_start + 3 : fence_end]
            if s.lower().startswith("json\n"):
                s = s[5:]
    try:
        return json.loads(s)
    except Exception as exc:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except Exception as inner_exc:
                logger.warning("JSON解析失败，尝试截取主体内容仍失败: %s", inner_exc)
                raise JSONParseError(text, f"JSON解析失败: {inner_exc}") from inner_exc
        logger.warning("JSON解析失败: %s", exc)
        raise JSONParseError(text, f"JSON解析失败: {exc}") from exc

class RecommendationExecutor:
    def __init__(self):
        self._client = None
        self._mock = True
        try:
            from src.utils.llm import UnifiedLLMClient

            self._client = UnifiedLLMClient("config/llm.yaml")
            self._mock = False
        except Exception:
            self._client = None
            self._mock = True

    def _mock_initial(self, theme: str, books: List[Dict]) -> Dict[str, Any]:
        quota = recommend_quota(len(books))
        scored = []
        for b in books:
            title = str(b.get("书名", ""))
            score = min(5.0, 2.0 + len(title) % 3 + 1.0)
            scored.append((score, b))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = []
        unselected_books = []
        for i, (score, b) in enumerate(scored):
            if i < quota:
                selected.append({
                    "id": str(b.get("书目条码", "")),
                    "title": str(b.get("书名", "")),
                    "rating": round(float(score), 1),
                    "reason": str(b.get("豆瓣内容简介", ""))[:200] or "内容综合较佳"
                })
            else:
                unselected_books.append({
                    "id": str(b.get("书目条码", "")),
                    "title": str(b.get("书名", ""))
                })
        return {
            "selected_books": selected,
            "unselected_books": [{
                "category": "竞争力不足",
                "explanation": "综合信息评分较低",
                "books": unselected_books
            }]
        }

    def _mock_final(self, books_with_reason: List[Dict]) -> Dict[str, Any]:
        quota = max(2, min(6, len(books_with_reason)))
        selected = []
        for i, b in enumerate(books_with_reason):
            if i < quota:
                selected.append({
                    "id": str(b.get("书目条码", "")),
                    "title": str(b.get("书名", "")),
                    "rating": 4.5,
                    "reason": str(b.get("初评理由", ""))[:200] or "综合理由充分"
                })
        unselected_books = [{
            "category": "与主题契合度较弱",
            "explanation": "初评理由相对薄弱",
            "books": [
                {"id": str(b.get("书目条码", "")), "title": str(b.get("书名", ""))}
                for b in books_with_reason[len(selected):]
            ]
        }] if len(books_with_reason) > len(selected) else []
        return {"selected_books": selected, "unselected_books": unselected_books}

    def _call_llm_with_structured_response(self, task_name: str, prompt: str, log_context: str) -> Dict[str, Any]:
        """统一处理结构化响应，使 JSON 错误触发重试链路。"""
        if not self._client:
            raise RuntimeError("LLM client 未初始化")

        def _handler(response_text: str) -> Dict[str, Any]:
            data = _safe_parse_json(response_text)
            if not isinstance(data, dict):
                raise JSONParseError(response_text, "LLM返回的不是JSON对象")
            return data

        logger.info("正在调用LLM | 任务=%s | %s", task_name, log_context)
        result = self._client.call(task_name, prompt, response_handler=_handler)
        logger.info("LLM调用完成 | 任务=%s | %s", task_name, log_context)
        return result

    def _create_error_result(self, books: List[Dict], error_msg: str) -> Dict[str, Any]:
        """创建错误结果，标记所有书目为错误状态"""
        error_books = []
        for b in books:
            error_books.append({
                "id": str(b.get("书目条码", "")),
                "title": str(b.get("书名", ""))
            })
        # 截断错误消息，避免过长
        short_msg = error_msg[:100] if len(error_msg) > 100 else error_msg
        full_msg = error_msg[:200] if len(error_msg) > 200 else error_msg
        return {
            "selected_books": [],
            "unselected_books": [{
                "category": f"ERROR: {short_msg}",
                "explanation": full_msg,
                "books": error_books
            }]
        }

    def initial(self, theme: str, books: List[Dict]) -> Dict[str, Any]:
        if self._mock:
            return self._mock_initial(theme, books)

        book_count = len(books)
        quota = recommend_quota(book_count)
        logger.info("准备调用LLM初评 | 主题=%s | 书目数=%d | 推荐配额=%d", theme, book_count, quota)

        prompt = build_initial_prompt(theme, books)
        try:
            data = self._call_llm_with_structured_response(
                "theme_initial",
                prompt,
                f"主题={theme} | 书目数={book_count}",
            )
            selected_count = len(data.get("selected_books", []))
            logger.info(
                "初评完成 | 主题=%s | 书目数=%d | 选中=%d | 未选中=%d",
                theme,
                book_count,
                selected_count,
                book_count - selected_count,
            )
            return data
        except Exception as e:
            error_msg = str(e)
            logger.error("初评调用失败 | 主题=%s | 错误=%s", theme, error_msg)
            return self._create_error_result(books, error_msg)


    def final(self, books_with_reason: List[Dict], top_n: int = 10) -> Dict[str, Any]:
        if self._mock:
            return self._mock_final(books_with_reason)

        book_count = len(books_with_reason)
        logger.info("准备调用LLM终评 | 候选书目数=%d | 目标Top=%d", book_count, top_n)

        prompt = build_final_prompt(books_with_reason, top_n)
        try:
            data = self._call_llm_with_structured_response(
                "theme_final",
                prompt,
                f"候选书目数={book_count} | Target={top_n}",
            )
            selected_count = len(data.get("selected_books", []))
            logger.info(
                "终评完成 | 候选书目数=%d | 最终选中=%d | 最终未选中=%d",
                book_count,
                selected_count,
                book_count - selected_count,
            )
            return data
        except Exception as e:
            error_msg = str(e)
            logger.error("终评调用失败 | 错误=%s", error_msg)
            return self._create_error_result(books_with_reason, error_msg)


    def runoff(self, theme: str, books: List[Dict], quota: int) -> Dict[str, Any]:
        """
        决选阶段执行逻辑

        参数:
            theme: 评审主题，例如"T"
            books: 初评通过后的书目列表
            quota: 决选配额（默认8本）

        返回:
            {"selected_books": [...], "unselected_books": [...]}
        """
        if self._mock:
            selected = []
            for i, b in enumerate(books):
                if i < quota:
                    selected.append({
                        "id": str(b.get("书目条码", "")),
                        "title": str(b.get("书名", "")),
                        "rating": 4.0,
                        "reason": "综合表现更优"
                    })
            unselected_books = [
                {"id": str(b.get("书目条码", "")), "title": str(b.get("书名", ""))}
                for b in books[quota:]
            ]
            return {
                "selected_books": selected,
                "unselected_books": [{
                    "category": "决选未入围",
                    "explanation": "信息维度综合得分略低",
                    "books": unselected_books
                }] if unselected_books else []
            }

        book_count = len(books)
        logger.info("准备调用LLM进行决选 | 主题=%s | 书目数=%d | 配额=%d", theme, book_count, quota)

        prompt = build_runoff_prompt(theme, books, quota)
        try:
            data = self._call_llm_with_structured_response(
                "theme_runoff",
                prompt,
                f"主题={theme} | 书目数={book_count} | 配额={quota}",
            )
            selected_count = len(data.get("selected_books", []))
            logger.info(
                "决选完成 | 主题=%s | 书目数=%d | 选中=%d | 未选中=%d",
                theme,
                book_count,
                selected_count,
                book_count - selected_count,
            )
            return data
        except Exception as e:
            error_msg = str(e)
            logger.error("决选调用失败 | 主题=%s | 错误=%s", theme, error_msg)
            return self._create_error_result(books, error_msg)


    def semifinal(self, books: List[Dict], quota: int) -> Dict[str, Any]:
        """
        锦标赛半决赛执行逻辑

        参数:
            books: 一组书目列表
            quota: 晋级配额（通常为组内数量的50%）

        返回:
            {"selected_books": [...], "unselected_books": [...]}
        """
        if self._mock:
            selected = []
            for i, b in enumerate(books):
                if i < quota:
                    selected.append({
                        "id": str(b.get("书目条码", "")),
                        "title": str(b.get("书名", "")),
                        "rating": 4.5,
                        "reason": "半决赛表现优秀"
                    })
            unselected_books = [
                {"id": str(b.get("书目条码", "")), "title": str(b.get("书名", ""))}
                for b in books[quota:]
            ]
            return {
                "selected_books": selected,
                "unselected_books": [{
                    "category": "半决赛未晋级",
                    "explanation": "竞争激烈，略逊一筹",
                    "books": unselected_books
                }] if unselected_books else []
            }

        book_count = len(books)
        logger.info("准备调用LLM进行半决赛评审 | 书目数=%d | 配额=%d", book_count, quota)

        prompt = build_semifinal_prompt(books, quota)
        try:
            data = self._call_llm_with_structured_response(
                "theme_semifinal",
                prompt,
                f"书目数={book_count} | 配额={quota}",
            )
            selected_count = len(data.get("selected_books", []))
            logger.info(
                "半决赛完成 | 书目数=%d | 晋级=%d | 淘汰=%d",
                book_count,
                selected_count,
                book_count - selected_count,
            )
            return data
        except Exception as e:
            error_msg = str(e)
            logger.error("半决赛调用失败 | 错误=%s", error_msg)
            return self._create_error_result(books, error_msg)


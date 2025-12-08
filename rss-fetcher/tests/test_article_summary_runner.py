import copy

from src.core.article_summary_runner import ArticleSummaryRunner


class StubStorage:
    """用于隔离文件读写的存储桩"""

    def __init__(self, articles, filepath="dummy.xlsx"):
        self._articles = articles
        self.filepath = filepath
        self.saved_batches = []

    def find_latest_stage_file(self, stage):
        return self.filepath

    def load_stage_data(self, stage, filepath):
        assert stage == "analyze"
        return self._articles

    def save_analyze_results(self, articles, filepath, skip_processed=True):
        # 保留副本，避免引用被后续修改影响
        self.saved_batches.append(copy.deepcopy(articles))
        return filepath


class StubSummaryAgent:
    """可控返回值的 Agent 桩"""

    def __init__(self, responses):
        self._responses = list(responses)

    def summarize(self, article):
        if not self._responses:
            raise RuntimeError("无可用响应")
        response = self._responses.pop(0)
        if callable(response):
            return response(article)
        return response


def _base_article(**overrides):
    base = {
        "title": "test",
        "filter_pass": True,
        "full_text": "内容",
        "llm_summary": "",
        "llm_summary_status": "",
        "llm_summary_error": "",
    }
    base.update(overrides)
    return base


def test_select_pending_articles_filters_successful_entries():
    articles = [
        _base_article(title="pass_and_done", llm_summary_status="成功", llm_summary="ok"),
        _base_article(title="need_summary"),
        _base_article(title="filtered_out", filter_pass=False),
    ]
    storage = StubStorage([])
    agent = StubSummaryAgent([])
    runner = ArticleSummaryRunner(storage, agent)

    pending = runner._select_pending_articles(articles)

    assert len(pending) == 1
    assert pending[0]["title"] == "need_summary"


def test_run_triggers_immediate_saves():
    articles = [
        _base_article(title="a1"),
        _base_article(title="a2"),
    ]
    responses = [
        {"llm_summary": "S1", "llm_summary_status": "成功", "llm_summary_error": None},
        {"llm_summary": "S2", "llm_summary_status": "成功", "llm_summary_error": None},
    ]
    storage = StubStorage(articles)
    agent = StubSummaryAgent(responses)
    runner = ArticleSummaryRunner(storage, agent)

    runner.run("dummy.xlsx")

    assert len(storage.saved_batches) == 2, "每完成一条应即时保存"
    assert articles[0]["llm_summary_status"] == "成功"
    assert articles[1]["llm_summary"] == "S2"


def test_run_performs_retry_for_failed_articles():
    articles = [_base_article(title="need_retry")]
    responses = [
        {"llm_summary": "", "llm_summary_status": "失败", "llm_summary_error": "网络错误"},
        {"llm_summary": "最终摘要", "llm_summary_status": "成功", "llm_summary_error": None},
    ]
    storage = StubStorage(articles)
    agent = StubSummaryAgent(responses)
    runner = ArticleSummaryRunner(storage, agent, max_attempts=2)

    runner.run("dummy.xlsx")

    assert articles[0]["llm_summary_status"] == "成功"
    assert len(storage.saved_batches) == 2, "失败后应再次保存重试结果"


def test_run_persists_error_when_retry_exhausted():
    articles = [_base_article(title="still_failed")]
    responses = [
        {"llm_summary": "", "llm_summary_status": "失败", "llm_summary_error": "超时"},
        {"llm_summary": "", "llm_summary_status": "失败", "llm_summary_error": "超时"},
    ]
    storage = StubStorage(articles)
    agent = StubSummaryAgent(responses)
    runner = ArticleSummaryRunner(storage, agent, max_attempts=2)

    runner.run("dummy.xlsx")

    assert articles[0]["llm_summary_status"] == "失败"
    assert "超时" in str(articles[0]["llm_summary_error"])
    assert len(storage.saved_batches) == 2

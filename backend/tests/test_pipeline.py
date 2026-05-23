"""End-to-end pipeline test: trend scraping → script generation.

All external I/O (Google Trends, Reddit, Anthropic API, DB) is mocked.
The test asserts that a valid ScriptOutput emerges from the other end.
"""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.script import ScriptOutput, SegmentType
from app.workers.script_worker import generate_script
from app.workers.trend_worker import scrape_trends


# ── shared test payload ────────────────────────────────────────────────────────

VALID_SCRIPT_PAYLOAD = {
    "title": "OpenAI Just Changed Everything — Here's What You Missed",
    "description": "The new AI release no one is talking about and why it matters to you.",
    "tags": ["AI", "OpenAI", "technology", "shorts", "viral"],
    "segments": [
        {
            "type": "hook",
            "text": "OpenAI just dropped something that will change your life.",
            "start_sec": 0,
            "end_sec": 2,
            "visual_keywords": ["AI robot", "technology"],
        },
        {
            "type": "escalation",
            "text": "Most people have no idea what just happened — and they are already falling behind.",
            "start_sec": 2,
            "end_sec": 10,
            "visual_keywords": ["news alert", "developer screen"],
        },
        {
            "type": "payoff",
            "text": "Here is exactly what dropped, why it matters, and three ways to use it today.",
            "start_sec": 10,
            "end_sec": 25,
            "visual_keywords": ["code editor", "AI demo", "laptop"],
        },
        {
            "type": "twist",
            "text": "But here is the part nobody is mentioning — it could replace your job in six months.",
            "start_sec": 25,
            "end_sec": 40,
            "visual_keywords": ["office", "layoff news"],
        },
        {
            "type": "cta",
            "text": "Follow for daily AI updates so you are never the last to know.",
            "start_sec": 40,
            "end_sec": 60,
            "visual_keywords": ["subscribe button", "phone screen"],
        },
    ],
}

QUALIFYING_TREND = {
    "source": "google_trends",
    "niche": "ai",
    "topic": "OpenAI releases GPT-5",
    "virality_score": 88.0,
    "engagement_score": 76.0,
    "monetization_score": 85.0,
    "saturation_score": 12.0,
    "opportunity_score": 76.5,
    "velocity": 42.0,
    "raw_data": "{}",
}


def _make_anthropic_mock(payload: dict) -> MagicMock:
    """Return a mock Anthropic class whose .messages.create() returns *payload* as JSON."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = response
    mock_cls = MagicMock(return_value=client)
    return mock_cls


# ── pipeline connection tests ──────────────────────────────────────────────────


class TestPipelineConnection:
    """Verify that scrape_trends enqueues generate_script for qualifying signals."""

    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_qualifying_signal_enqueues_script_task(
        self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs_task
    ):
        video_id = str(uuid.uuid4())
        trend_id = str(uuid.uuid4())
        expected_job = {
            "video_id": video_id,
            "topic": QUALIFYING_TREND["topic"],
            "niche": "ai",
            "trend_signal_id": trend_id,
        }

        mock_gt.return_value = [QUALIFYING_TREND]
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = ([expected_job], 0)

        scrape_trends.apply(kwargs={"niche": "ai"}).get()

        mock_gs_task.apply_async.assert_called_once_with(kwargs=expected_job)

    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_multiple_qualifying_signals_enqueue_multiple_tasks(
        self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs_task
    ):
        jobs = [
            {"video_id": str(uuid.uuid4()), "topic": "Trend A", "niche": "ai", "trend_signal_id": str(uuid.uuid4())},
            {"video_id": str(uuid.uuid4()), "topic": "Trend B", "niche": "ai", "trend_signal_id": str(uuid.uuid4())},
        ]
        mock_gt.return_value = []
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = (jobs, 0)

        result = scrape_trends.apply(kwargs={"niche": "ai"}).get()

        assert mock_gs_task.apply_async.call_count == 2
        assert result["enqueued"] == 2

    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_no_qualifying_signals_nothing_enqueued(
        self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs_task
    ):
        mock_gt.return_value = []
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = ([], 0)

        result = scrape_trends.apply(kwargs={"niche": "ai"}).get()

        mock_gs_task.apply_async.assert_not_called()
        assert result["enqueued"] == 0


# ── script worker output validation ───────────────────────────────────────────


class TestScriptWorkerOutput:
    """Verify that generate_script produces a valid ScriptOutput when Anthropic is mocked."""

    def _setup_anthropic(self, mock_anthropic_cls: MagicMock, payload: dict = VALID_SCRIPT_PAYLOAD) -> None:
        mock_anthropic_cls.return_value = _make_anthropic_mock(payload).return_value

    # Decorator order (bottom → top) maps to parameter order (left → right after self).
    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_output_validates_as_script_schema(self, mock_cls, mock_asyncio_run, mock_voice):
        self._setup_anthropic(mock_cls)
        mock_asyncio_run.return_value = None

        result = generate_script.apply(
            kwargs={
                "video_id": str(uuid.uuid4()),
                "topic": "OpenAI releases GPT-5",
                "niche": "ai",
            }
        ).get()

        script = ScriptOutput.model_validate(result["script"])
        assert len(script.segments) == 5

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_segment_order_is_correct(self, mock_cls, mock_asyncio_run, mock_voice):
        self._setup_anthropic(mock_cls)
        mock_asyncio_run.return_value = None

        result = generate_script.apply(
            kwargs={
                "video_id": str(uuid.uuid4()),
                "topic": "OpenAI releases GPT-5",
                "niche": "ai",
            }
        ).get()

        script = ScriptOutput.model_validate(result["script"])
        actual_types = [s.type for s in script.segments]
        assert actual_types == [t.value for t in SegmentType]

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_result_carries_video_id_and_model(self, mock_cls, mock_asyncio_run, mock_voice):
        self._setup_anthropic(mock_cls)
        mock_asyncio_run.return_value = None
        video_id = str(uuid.uuid4())

        result = generate_script.apply(
            kwargs={"video_id": video_id, "topic": "test", "niche": "ai"}
        ).get()

        assert result["video_id"] == video_id
        assert result["model_used"] == "claude-sonnet-4-20250514"

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_visual_keywords_present_in_all_segments(self, mock_cls, mock_asyncio_run, mock_voice):
        self._setup_anthropic(mock_cls)
        mock_asyncio_run.return_value = None

        result = generate_script.apply(
            kwargs={"video_id": str(uuid.uuid4()), "topic": "test", "niche": "ai"}
        ).get()

        script = ScriptOutput.model_validate(result["script"])
        for seg in script.segments:
            assert len(seg.visual_keywords) >= 1, f"{seg.type} segment has no visual keywords"


# ── full end-to-end pipeline ───────────────────────────────────────────────────


class TestFullPipeline:
    """Simulate a complete trend → script cycle with all external I/O mocked."""

    # Decorators bottom → top; parameters left → right after self.
    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_trend_to_valid_script_output(
        self,
        mock_gt,
        mock_reddit,
        mock_asyncio_run_trend,
        mock_gs_task,
        mock_anthropic_cls,
        mock_asyncio_run_script,
        mock_voice,
    ):
        video_id = str(uuid.uuid4())
        trend_id = str(uuid.uuid4())
        topic = QUALIFYING_TREND["topic"]
        niche = "ai"

        # ── Phase 1: trend scraper ─────────────────────────────────────────────
        mock_gt.return_value = [QUALIFYING_TREND]
        mock_reddit.return_value = []
        pipeline_job = {"video_id": video_id, "topic": topic, "niche": niche, "trend_signal_id": trend_id}
        mock_asyncio_run_trend.return_value = ([pipeline_job], 0)

        trend_result = scrape_trends.apply(kwargs={"niche": niche}).get()

        assert trend_result["qualifying"] == 1
        assert trend_result["enqueued"] == 1
        mock_gs_task.apply_async.assert_called_once_with(kwargs=pipeline_job)

        # ── Phase 2: script worker ─────────────────────────────────────────────
        mock_anthropic_cls.return_value = _make_anthropic_mock(VALID_SCRIPT_PAYLOAD).return_value
        # asyncio.run returns None for _load_trend_data (trend_data=None → kwargs fallback)
        # and None for _persist_script_result.
        mock_asyncio_run_script.return_value = None

        script_result = generate_script.apply(kwargs=pipeline_job).get()

        # ── Assert a valid ScriptOutput came out the other end ────────────────
        script = ScriptOutput.model_validate(script_result["script"])
        script.validate_segment_order()

        assert script.title == VALID_SCRIPT_PAYLOAD["title"]
        assert script.segments[0].type == SegmentType.hook
        assert script.segments[4].type == SegmentType.cta
        assert script_result["video_id"] == video_id
        assert script_result["trend_signal_id"] == trend_id
        assert all(len(s.visual_keywords) >= 1 for s in script.segments)
        mock_voice.apply_async.assert_called_once()

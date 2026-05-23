"""Pipeline chain tests — verifies the enqueue edge between every adjacent worker pair.

Each test class targets one handoff edge:
  TestTrendToScriptChain  — scrape_trends → generate_script.apply_async
  TestScriptToVoiceChain  — generate_script → synthesize_voice.apply_async
  TestVoiceToVisualChain  — synthesize_voice → fetch_visuals.apply_async

All external I/O (Google Trends, Reddit, Anthropic, ElevenLabs) is mocked.
The downstream task is also mocked so only the enqueue call is asserted.
"""

import base64
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.workers.script_worker import generate_script
from app.workers.trend_worker import scrape_trends
from app.workers.voice_worker import synthesize_voice


# ── shared test data ───────────────────────────────────────────────────────────

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

VALID_SCRIPT_DICT = {
    "title": "AI Just Changed Everything",
    "description": "What you need to know right now.",
    "tags": ["AI", "tech", "shorts"],
    "segments": [
        {
            "type": "hook",
            "text": "Stop scrolling.",
            "start_sec": 0,
            "end_sec": 2,
            "visual_keywords": ["tech"],
        },
        {
            "type": "escalation",
            "text": "Here is why this matters.",
            "start_sec": 2,
            "end_sec": 10,
            "visual_keywords": ["news"],
        },
        {
            "type": "payoff",
            "text": "The truth nobody ever tells you.",
            "start_sec": 10,
            "end_sec": 25,
            "visual_keywords": ["insight"],
        },
        {
            "type": "twist",
            "text": "But wait — there is even more to this.",
            "start_sec": 25,
            "end_sec": 40,
            "visual_keywords": ["twist"],
        },
        {
            "type": "cta",
            "text": "Follow for daily updates.",
            "start_sec": 40,
            "end_sec": 60,
            "visual_keywords": ["subscribe"],
        },
    ],
}

FAKE_AUDIO_BYTES = b"\xff\xfb\x90\x00" * 64


def _make_anthropic_mock(payload: dict) -> MagicMock:
    """Return a patched Anthropic class whose messages.create() returns *payload* as JSON."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = response
    mock_cls = MagicMock(return_value=client)
    return mock_cls


def _make_elevenlabs_response() -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "audio_base64": base64.b64encode(FAKE_AUDIO_BYTES).decode(),
        "alignment": {"words": [{"word": "Stop", "start": 0.0, "end": 0.3}]},
    }
    return mock_resp


# ── chain: trend → script ──────────────────────────────────────────────────────


class TestTrendToScriptChain:
    """A qualifying trend signal must auto-enqueue generate_script."""

    # Decorator order bottom → top maps to parameters left → right after self.
    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_qualifying_signal_enqueues_script_task(
        self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs_task
    ):
        video_id = str(uuid.uuid4())
        trend_id = str(uuid.uuid4())
        job = {
            "video_id": video_id,
            "topic": QUALIFYING_TREND["topic"],
            "niche": "ai",
            "trend_signal_id": trend_id,
        }
        mock_gt.return_value = [QUALIFYING_TREND]
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = ([job], 0)

        scrape_trends.apply(kwargs={"niche": "ai"}).get()

        mock_gs_task.apply_async.assert_called_once_with(kwargs=job)

    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_enqueued_kwargs_carry_all_required_fields(
        self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs_task
    ):
        video_id = str(uuid.uuid4())
        trend_id = str(uuid.uuid4())
        job = {
            "video_id": video_id,
            "topic": "AI news",
            "niche": "ai",
            "trend_signal_id": trend_id,
        }
        mock_gt.return_value = [QUALIFYING_TREND]
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = ([job], 0)

        scrape_trends.apply(kwargs={"niche": "ai"}).get()

        actual = mock_gs_task.apply_async.call_args.kwargs["kwargs"]
        assert actual["video_id"] == video_id
        assert actual["topic"] == "AI news"
        assert actual["niche"] == "ai"
        assert actual["trend_signal_id"] == trend_id

    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_below_threshold_signal_never_enqueues(
        self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs_task
    ):
        mock_gt.return_value = []
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = ([], 0)

        result = scrape_trends.apply(kwargs={"niche": "ai"}).get()

        mock_gs_task.apply_async.assert_not_called()
        assert result["enqueued"] == 0

    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_multiple_qualifying_signals_each_produce_independent_task(
        self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs_task
    ):
        jobs = [
            {
                "video_id": str(uuid.uuid4()),
                "topic": f"Trend {i}",
                "niche": "ai",
                "trend_signal_id": str(uuid.uuid4()),
            }
            for i in range(3)
        ]
        mock_gt.return_value = []
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = (jobs, 0)

        result = scrape_trends.apply(kwargs={"niche": "ai"}).get()

        assert mock_gs_task.apply_async.call_count == 3
        assert result["enqueued"] == 3


# ── chain: script → voice ──────────────────────────────────────────────────────


class TestScriptToVoiceChain:
    """Completing script generation must enqueue synthesize_voice with full script_json."""

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_voice_task_enqueued_after_successful_script(
        self, mock_anthropic_cls, mock_asyncio_run, mock_voice
    ):
        mock_anthropic_cls.return_value = _make_anthropic_mock(VALID_SCRIPT_DICT).return_value
        mock_asyncio_run.return_value = None

        generate_script.apply(
            kwargs={"video_id": str(uuid.uuid4()), "topic": "AI news", "niche": "ai"}
        ).get()

        mock_voice.apply_async.assert_called_once()

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_voice_task_receives_correct_video_id(
        self, mock_anthropic_cls, mock_asyncio_run, mock_voice
    ):
        mock_anthropic_cls.return_value = _make_anthropic_mock(VALID_SCRIPT_DICT).return_value
        mock_asyncio_run.return_value = None
        video_id = str(uuid.uuid4())

        generate_script.apply(
            kwargs={"video_id": video_id, "topic": "AI news", "niche": "ai"}
        ).get()

        enqueued = mock_voice.apply_async.call_args.kwargs["kwargs"]
        assert enqueued["video_id"] == video_id

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_voice_task_receives_five_segment_script_json(
        self, mock_anthropic_cls, mock_asyncio_run, mock_voice
    ):
        mock_anthropic_cls.return_value = _make_anthropic_mock(VALID_SCRIPT_DICT).return_value
        mock_asyncio_run.return_value = None

        generate_script.apply(
            kwargs={"video_id": str(uuid.uuid4()), "topic": "AI news", "niche": "ai"}
        ).get()

        enqueued = mock_voice.apply_async.call_args.kwargs["kwargs"]
        script_json = enqueued["script_json"]
        assert "segments" in script_json
        assert len(script_json["segments"]) == 5
        assert script_json["segments"][0]["type"] == "hook"
        assert script_json["segments"][4]["type"] == "cta"

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_voice_not_enqueued_when_llm_returns_invalid_json(
        self, mock_anthropic_cls, mock_asyncio_run, mock_voice
    ):
        """If the LLM response can't be parsed, the pipeline must not advance to voice."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        content_block = MagicMock()
        content_block.text = "NOT VALID JSON"
        mock_client.messages.create.return_value.content = [content_block]
        mock_asyncio_run.return_value = None

        with pytest.raises(Exception):
            generate_script.apply(
                kwargs={"video_id": str(uuid.uuid4()), "topic": "AI news", "niche": "ai"}
            ).get()

        mock_voice.apply_async.assert_not_called()


# ── chain: voice → visual ──────────────────────────────────────────────────────


class TestVoiceToVisualChain:
    """After TTS (or skip), fetch_visuals must be enqueued with the correct arguments."""

    # Decorator order bottom → top maps to parameters left → right after self.
    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_fetch_visuals_enqueued_after_successful_tts(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue, tmp_path
    ):
        video_id = str(uuid.uuid4())
        mock_client = MagicMock()
        mock_httpx_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = _make_elevenlabs_response()
        mock_settings.elevenlabs_api_key = "test-key"
        mock_settings.elevenlabs_voice_id = "test-voice"
        mock_settings.media_dir = str(tmp_path)

        synthesize_voice.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_DICT}
        ).get()

        mock_enqueue.assert_called_once_with(video_id, VALID_SCRIPT_DICT)

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_fetch_visuals_enqueued_even_when_tts_key_absent(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        """Pipeline must not stall when ELEVENLABS_API_KEY is missing."""
        video_id = str(uuid.uuid4())
        mock_settings.elevenlabs_api_key = ""

        synthesize_voice.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_DICT}
        ).get()

        mock_enqueue.assert_called_once_with(video_id, VALID_SCRIPT_DICT)
        mock_httpx_cls.assert_not_called()

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_fetch_visuals_receives_full_script_json(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue, tmp_path
    ):
        video_id = str(uuid.uuid4())
        mock_client = MagicMock()
        mock_httpx_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = _make_elevenlabs_response()
        mock_settings.elevenlabs_api_key = "test-key"
        mock_settings.elevenlabs_voice_id = "test-voice"
        mock_settings.media_dir = str(tmp_path)

        synthesize_voice.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_DICT}
        ).get()

        _, passed_script = mock_enqueue.call_args.args
        assert passed_script["segments"][0]["type"] == "hook"
        assert len(passed_script["segments"]) == 5

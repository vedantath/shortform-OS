"""Tests for the script generation worker."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.script import ScriptOutput, SegmentType
from app.workers.script_worker import _call_anthropic, generate_script


VALID_SCRIPT_DICT = {
    "title": "5 Tricks Nobody Tells You About Python",
    "description": "Level up your Python skills with these 5 hidden tricks.",
    "tags": ["python", "programming", "coding"],
    "segments": [
        {
            "type": "hook",
            "text": "Stop writing bad Python.",
            "start_sec": 0,
            "end_sec": 2,
            "visual_keywords": ["python", "code"],
        },
        {
            "type": "escalation",
            "text": "Most developers waste hours on problems that have one-line solutions.",
            "start_sec": 2,
            "end_sec": 10,
            "visual_keywords": ["developer", "laptop"],
        },
        {
            "type": "payoff",
            "text": "Here are five tricks senior devs use daily.",
            "start_sec": 10,
            "end_sec": 25,
            "visual_keywords": ["code", "terminal"],
        },
        {
            "type": "twist",
            "text": "But wait — there's a catch most tutorials skip.",
            "start_sec": 25,
            "end_sec": 40,
            "visual_keywords": ["surprise", "code"],
        },
        {
            "type": "cta",
            "text": "Follow for daily Python tips.",
            "start_sec": 40,
            "end_sec": 60,
            "visual_keywords": ["subscribe", "coding"],
        },
    ],
}


def _make_anthropic_response(data: dict) -> MagicMock:
    content_block = MagicMock()
    content_block.text = json.dumps(data)
    response = MagicMock()
    response.content = [content_block]
    return response


class TestScriptOutput:
    def test_valid_script_parses(self):
        script = ScriptOutput.model_validate(VALID_SCRIPT_DICT)
        assert script.title == VALID_SCRIPT_DICT["title"]
        assert len(script.segments) == 5

    def test_segment_order_validates(self):
        script = ScriptOutput.model_validate(VALID_SCRIPT_DICT)
        validated = script.validate_segment_order()
        assert validated is script

    def test_wrong_segment_order_raises(self):
        bad = dict(VALID_SCRIPT_DICT)
        bad["segments"] = list(reversed(VALID_SCRIPT_DICT["segments"]))
        script = ScriptOutput.model_validate(bad)
        with pytest.raises(AssertionError):
            script.validate_segment_order()

    def test_missing_segment_raises(self):
        from pydantic import ValidationError

        bad = dict(VALID_SCRIPT_DICT)
        bad["segments"] = VALID_SCRIPT_DICT["segments"][:4]
        with pytest.raises(ValidationError):
            ScriptOutput.model_validate(bad)


class TestCallAnthropic:
    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_returns_script_output(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = _make_anthropic_response(VALID_SCRIPT_DICT)

        result = _call_anthropic(
            topic="Python tricks", niche="programming", hook_pattern="bold-claim"
        )

        assert isinstance(result, ScriptOutput)
        assert result.title == VALID_SCRIPT_DICT["title"]
        mock_client.messages.create.assert_called_once()

    @patch("app.workers.script_worker.anthropic.Anthropic")
    def test_raises_on_invalid_json(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        content_block = MagicMock()
        content_block.text = "not json"
        mock_client.messages.create.return_value.content = [content_block]

        with pytest.raises(Exception):
            _call_anthropic(topic="test", niche="test", hook_pattern="bold-claim")


class TestGenerateScriptTask:
    # Decorator order (bottom → top) maps to parameter order (left → right after self).
    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker._call_anthropic")
    def test_task_returns_result_dict(self, mock_call, mock_asyncio_run, mock_voice):
        mock_call.return_value = ScriptOutput.model_validate(VALID_SCRIPT_DICT)
        mock_asyncio_run.return_value = None  # _persist_script_result returns None

        result = generate_script.apply(
            kwargs={
                "video_id": "test-video-id",
                "topic": "Python tricks",
                "niche": "programming",
            }
        ).get()

        assert result["video_id"] == "test-video-id"
        assert "script" in result
        assert result["script"]["title"] == VALID_SCRIPT_DICT["title"]
        mock_voice.apply_async.assert_called_once()

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker._call_anthropic")
    def test_hook_pattern_in_result(self, mock_call, mock_asyncio_run, mock_voice):
        mock_call.return_value = ScriptOutput.model_validate(VALID_SCRIPT_DICT)
        mock_asyncio_run.return_value = None

        result = generate_script.apply(
            kwargs={
                "video_id": "test-video-id",
                "topic": "Python tricks",
                "niche": "ai",
            }
        ).get()

        assert result["hook_pattern"] == "shocking-prediction"
        assert result["model_used"] == "claude-sonnet-4-20250514"

    @patch("app.workers.script_worker.synthesize_voice")
    @patch("app.workers.script_worker.asyncio.run")
    @patch("app.workers.script_worker._call_anthropic")
    def test_voice_task_enqueued_with_correct_kwargs(
        self, mock_call, mock_asyncio_run, mock_voice
    ):
        video_id = "test-video-id-789"
        mock_call.return_value = ScriptOutput.model_validate(VALID_SCRIPT_DICT)
        mock_asyncio_run.return_value = None

        generate_script.apply(
            kwargs={"video_id": video_id, "topic": "test", "niche": "ai"}
        ).get()

        call_kwargs = mock_voice.apply_async.call_args.kwargs["kwargs"]
        assert call_kwargs["video_id"] == video_id
        assert "script_json" in call_kwargs

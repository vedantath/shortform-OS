"""Tests for the voice synthesis worker.

Covers: file output, timestamps schema, no-key skip behavior, retry on HTTP errors,
and downstream fetch_visuals enqueue.
"""

import base64
import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx as httpx_module
import pytest

from app.workers.voice_worker import synthesize_voice


# ── shared test data ───────────────────────────────────────────────────────────

VALID_SCRIPT_JSON = {
    "title": "AI Just Changed Everything",
    "description": "What you need to know right now.",
    "tags": ["AI", "tech"],
    "segments": [
        {
            "type": "hook",
            "text": "Stop scrolling.",
            "start_sec": 0,
            "end_sec": 2,
            "visual_keywords": ["hook"],
        },
        {
            "type": "escalation",
            "text": "Here is why this matters to you.",
            "start_sec": 2,
            "end_sec": 10,
            "visual_keywords": ["escalation"],
        },
        {
            "type": "payoff",
            "text": "The truth nobody ever tells you.",
            "start_sec": 10,
            "end_sec": 25,
            "visual_keywords": ["payoff"],
        },
        {
            "type": "twist",
            "text": "But wait — there is even more to this story.",
            "start_sec": 25,
            "end_sec": 40,
            "visual_keywords": ["twist"],
        },
        {
            "type": "cta",
            "text": "Follow for daily tips and updates.",
            "start_sec": 40,
            "end_sec": 60,
            "visual_keywords": ["cta"],
        },
    ],
}

FAKE_AUDIO_BYTES = b"\xff\xfb\x90\x00" * 64  # plausible MP3-header bytes repeated

FAKE_WORD_TIMESTAMPS = [
    {"word": "Stop", "start": 0.0, "end": 0.25},
    {"word": "scrolling.", "start": 0.3, "end": 0.65},
    {"word": "Here", "start": 0.7, "end": 0.9},
    {"word": "is", "start": 0.95, "end": 1.05},
]


def _make_elevenlabs_response(
    audio_bytes: bytes = FAKE_AUDIO_BYTES,
    words: list[dict] | None = None,
) -> MagicMock:
    """Build a mock httpx response matching the ElevenLabs with-timestamps endpoint."""
    if words is None:
        words = FAKE_WORD_TIMESTAMPS
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "audio_base64": base64.b64encode(audio_bytes).decode(),
        "alignment": {"words": words},
    }
    return mock_resp


def _make_http_status_error(status_code: int) -> httpx_module.HTTPStatusError:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    return httpx_module.HTTPStatusError(
        str(status_code), request=MagicMock(), response=mock_response
    )


# ── helpers ────────────────────────────────────────────────────────────────────


def _run_success(tmp_path: Path, video_id: str, *, words=None, audio_bytes=None) -> dict:
    """Run synthesize_voice with all external I/O mocked; return the task result."""
    mock_client = MagicMock()
    mock_client.post.return_value = _make_elevenlabs_response(
        audio_bytes=audio_bytes or FAKE_AUDIO_BYTES,
        words=words if words is not None else FAKE_WORD_TIMESTAMPS,
    )
    with (
        patch("app.workers.voice_worker.httpx.Client") as mock_cls,
        patch("app.workers.voice_worker.asyncio.run"),
        patch("app.workers.voice_worker._enqueue_visuals"),
        patch("app.workers.voice_worker.settings") as mock_settings,
    ):
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_settings.elevenlabs_api_key = "test-key"
        mock_settings.elevenlabs_voice_id = "test-voice-id"
        mock_settings.media_dir = str(tmp_path)
        return synthesize_voice.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
        ).get()


# ── file output ────────────────────────────────────────────────────────────────


class TestSynthesizeVoiceFiles:
    """narration.mp3 and timestamps.json must be written under MEDIA_DIR/{video_id}/."""

    def test_audio_file_is_created(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_success(tmp_path, video_id)
        assert (tmp_path / video_id / "narration.mp3").exists()

    def test_audio_file_contents_match_decoded_api_response(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_success(tmp_path, video_id, audio_bytes=FAKE_AUDIO_BYTES)
        written = (tmp_path / video_id / "narration.mp3").read_bytes()
        assert written == FAKE_AUDIO_BYTES

    def test_timestamps_file_is_created(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_success(tmp_path, video_id)
        assert (tmp_path / video_id / "timestamps.json").exists()

    def test_timestamps_json_schema_matches_elevenlabs_alignment_words(self, tmp_path):
        """Each entry must carry word, start, end — the ElevenLabs alignment.words shape."""
        video_id = str(uuid.uuid4())
        _run_success(tmp_path, video_id)

        data = json.loads((tmp_path / video_id / "timestamps.json").read_text())
        assert isinstance(data, list)
        assert len(data) == len(FAKE_WORD_TIMESTAMPS)
        for entry in data:
            assert "word" in entry, f"missing 'word' key in {entry}"
            assert "start" in entry, f"missing 'start' key in {entry}"
            assert "end" in entry, f"missing 'end' key in {entry}"
            assert isinstance(entry["start"], (int, float))
            assert isinstance(entry["end"], (int, float))

    def test_timestamps_values_round_trip_from_api_response(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_success(tmp_path, video_id)

        data = json.loads((tmp_path / video_id / "timestamps.json").read_text())
        assert data == FAKE_WORD_TIMESTAMPS

    def test_output_directory_created_automatically(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_success(tmp_path, video_id)
        assert (tmp_path / video_id).is_dir()

    def test_result_audio_path_points_to_correct_file(self, tmp_path):
        video_id = str(uuid.uuid4())
        result = _run_success(tmp_path, video_id)
        assert result["audio_path"].endswith("narration.mp3")
        assert video_id in result["audio_path"]

    def test_result_timestamps_path_points_to_correct_file(self, tmp_path):
        video_id = str(uuid.uuid4())
        result = _run_success(tmp_path, video_id)
        assert result["timestamps_path"].endswith("timestamps.json")
        assert video_id in result["timestamps_path"]

    def test_result_word_count_matches_api_response(self, tmp_path):
        video_id = str(uuid.uuid4())
        result = _run_success(tmp_path, video_id)
        assert result["word_count"] == len(FAKE_WORD_TIMESTAMPS)

    def test_result_status_is_voiced(self, tmp_path):
        video_id = str(uuid.uuid4())
        result = _run_success(tmp_path, video_id)
        assert result["status"] == "voiced"

    def test_result_video_id_echoed(self, tmp_path):
        video_id = str(uuid.uuid4())
        result = _run_success(tmp_path, video_id)
        assert result["video_id"] == video_id


# ── no-key skip behavior ───────────────────────────────────────────────────────


class TestSynthesizeVoiceSkip:
    """When ELEVENLABS_API_KEY is empty the task must skip TTS and still advance the pipeline."""

    # Decorator order: bottom → first param after self.
    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_status_is_voice_skipped(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.elevenlabs_api_key = ""
        result = synthesize_voice.apply(
            kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
        ).get()
        assert result["status"] == "voice_skipped"

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_video_id_present_in_result(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.elevenlabs_api_key = ""
        video_id = str(uuid.uuid4())
        result = synthesize_voice.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
        ).get()
        assert result["video_id"] == video_id

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_no_http_request_made(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.elevenlabs_api_key = ""
        synthesize_voice.apply(
            kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
        ).get()
        mock_httpx_cls.assert_not_called()

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_db_status_updated(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.elevenlabs_api_key = ""
        synthesize_voice.apply(
            kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
        ).get()
        mock_asyncio_run.assert_called_once()

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_fetch_visuals_still_enqueued(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        """Pipeline must not stall when TTS key is absent."""
        mock_settings.elevenlabs_api_key = ""
        video_id = str(uuid.uuid4())
        synthesize_voice.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
        ).get()
        mock_enqueue.assert_called_once_with(video_id, VALID_SCRIPT_JSON)


# ── retry behavior ─────────────────────────────────────────────────────────────


class TestSynthesizeVoiceRetry:
    """HTTP errors from ElevenLabs must trigger Celery retry."""

    def _run_with_http_error(self, tmp_path: Path, status_code: int) -> None:
        mock_client = MagicMock()
        exc = _make_http_status_error(status_code)
        mock_client.post.return_value.raise_for_status.side_effect = exc

        with (
            patch("app.workers.voice_worker.httpx.Client") as mock_cls,
            patch("app.workers.voice_worker.asyncio.run"),
            patch("app.workers.voice_worker.settings") as mock_settings,
        ):
            mock_cls.return_value.__enter__.return_value = mock_client
            mock_settings.elevenlabs_api_key = "test-key"
            mock_settings.elevenlabs_voice_id = "test-voice"
            mock_settings.media_dir = str(tmp_path)
            synthesize_voice.apply(
                kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
            ).get()

    def test_rate_limit_429_raises_after_max_retries(self, tmp_path):
        with pytest.raises(Exception):
            self._run_with_http_error(tmp_path, 429)

    def test_server_error_500_raises_after_max_retries(self, tmp_path):
        with pytest.raises(Exception):
            self._run_with_http_error(tmp_path, 500)

    def test_rate_limit_does_not_write_files(self, tmp_path):
        """When TTS fails with 429, no partial output files should be written."""
        video_id = str(uuid.uuid4())
        mock_client = MagicMock()
        exc = _make_http_status_error(429)
        mock_client.post.return_value.raise_for_status.side_effect = exc

        with (
            patch("app.workers.voice_worker.httpx.Client") as mock_cls,
            patch("app.workers.voice_worker.asyncio.run"),
            patch("app.workers.voice_worker.settings") as mock_settings,
        ):
            mock_cls.return_value.__enter__.return_value = mock_client
            mock_settings.elevenlabs_api_key = "test-key"
            mock_settings.elevenlabs_voice_id = "test-voice"
            mock_settings.media_dir = str(tmp_path)
            try:
                synthesize_voice.apply(
                    kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
                ).get()
            except Exception:
                pass

        assert not (tmp_path / video_id / "narration.mp3").exists()

    def test_request_error_raises_after_max_retries(self, tmp_path):
        """Network-level errors (e.g. connection refused) also trigger retry."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx_module.RequestError("connection refused")

        with (
            patch("app.workers.voice_worker.httpx.Client") as mock_cls,
            patch("app.workers.voice_worker.asyncio.run"),
            patch("app.workers.voice_worker.settings") as mock_settings,
        ):
            mock_cls.return_value.__enter__.return_value = mock_client
            mock_settings.elevenlabs_api_key = "test-key"
            mock_settings.elevenlabs_voice_id = "test-voice"
            mock_settings.media_dir = str(tmp_path)

            with pytest.raises(Exception):
                synthesize_voice.apply(
                    kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
                ).get()


# ── downstream enqueue ─────────────────────────────────────────────────────────


class TestSynthesizeVoiceDownstream:
    """fetch_visuals must receive the video_id and full script_json."""

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_fetch_visuals_enqueued_with_video_id(
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
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
        ).get()

        mock_enqueue.assert_called_once_with(video_id, VALID_SCRIPT_JSON)

    @patch("app.workers.voice_worker._enqueue_visuals")
    @patch("app.workers.voice_worker.asyncio.run")
    @patch("app.workers.voice_worker.settings")
    @patch("app.workers.voice_worker.httpx.Client")
    def test_db_status_updated_to_voiced(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue, tmp_path
    ):
        mock_client = MagicMock()
        mock_httpx_cls.return_value.__enter__.return_value = mock_client
        mock_client.post.return_value = _make_elevenlabs_response()
        mock_settings.elevenlabs_api_key = "test-key"
        mock_settings.elevenlabs_voice_id = "test-voice"
        mock_settings.media_dir = str(tmp_path)

        synthesize_voice.apply(
            kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
        ).get()

        mock_asyncio_run.assert_called_once()

"""Tests for the visual fetch worker.

Covers: manifest structure, Pixabay fallback, no-key skip, 429 retry,
and pure helper logic (scoring, clip selection, keyword extraction).
"""

import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx as httpx_module
import pytest

from app.workers.visual_worker import (
    _best_pixabay_clip,
    _best_pixabay_file,
    _best_pexels_clip,
    _best_pexels_file,
    _keywords_for_segment,
    _score_clip,
    fetch_visuals,
)


# ── shared test data ───────────────────────────────────────────────────────────

FAKE_VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64

PEXELS_PORTRAIT_VIDEO = {
    "id": 101,
    "duration": 8,
    "video_files": [
        {
            "file_type": "video/mp4",
            "width": 1080,
            "height": 1920,
            "link": "https://player.vimeo.com/pexels_101.mp4",
        }
    ],
}

PEXELS_LANDSCAPE_VIDEO = {
    "id": 102,
    "duration": 10,
    "video_files": [
        {
            "file_type": "video/mp4",
            "width": 1920,
            "height": 1080,
            "link": "https://player.vimeo.com/pexels_102.mp4",
        }
    ],
}

PIXABAY_PORTRAIT_HIT = {
    "id": 201,
    "duration": 12,
    "videos": {
        "large": {
            "url": "https://cdn.pixabay.com/pixabay_201.mp4",
            "width": 1080,
            "height": 1920,
        }
    },
}

VALID_SCRIPT_JSON = {
    "title": "Test Video",
    "description": "Test",
    "tags": ["test"],
    "segments": [
        {"type": "hook",       "text": "Stop scrolling.",   "start_sec": 0,  "end_sec": 2,  "visual_keywords": ["technology", "AI robot"]},
        {"type": "escalation", "text": "Here is why.",      "start_sec": 2,  "end_sec": 10, "visual_keywords": ["news alert", "developer"]},
        {"type": "payoff",     "text": "The truth.",        "start_sec": 10, "end_sec": 25, "visual_keywords": ["code editor", "laptop"]},
        {"type": "twist",      "text": "But wait.",         "start_sec": 25, "end_sec": 40, "visual_keywords": ["office", "layoff"]},
        {"type": "cta",        "text": "Follow now.",       "start_sec": 40, "end_sec": 60, "visual_keywords": ["subscribe", "phone screen"]},
    ],
}

MANIFEST_REQUIRED_KEYS = {
    "segment_index", "segment_type", "local_path",
    "url", "duration", "width", "height", "source",
}


# ── HTTP mock factory ──────────────────────────────────────────────────────────

def _make_http_client(
    pexels_videos: list[dict],
    pixabay_hits: list[dict],
    download_bytes: bytes = FAKE_VIDEO_BYTES,
) -> MagicMock:
    mock_client = MagicMock()

    def _get(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "pexels.com" in str(url):
            resp.json.return_value = {"videos": pexels_videos}
        else:
            resp.json.return_value = {"hits": pixabay_hits}
        return resp

    mock_client.get.side_effect = _get

    stream_resp = MagicMock()
    stream_resp.raise_for_status = MagicMock()
    stream_resp.iter_bytes.return_value = iter([download_bytes])
    stream_cm = mock_client.stream.return_value
    stream_cm.__enter__.return_value = stream_resp
    stream_cm.__exit__ = MagicMock(return_value=False)

    return mock_client


def _run_task(
    tmp_path: Path,
    video_id: str,
    *,
    pexels_key: str = "pexels-key",
    pixabay_key: str = "pixabay-key",
    pexels_videos: list[dict] | None = None,
    pixabay_hits: list[dict] | None = None,
    download_bytes: bytes = FAKE_VIDEO_BYTES,
) -> tuple[dict, MagicMock]:
    """Run fetch_visuals eagerly with all external I/O mocked.

    Returns (result, mock_http_client) so callers can assert on the task
    result and which HTTP calls were made.
    """
    mock_client = _make_http_client(
        pexels_videos if pexels_videos is not None else [PEXELS_PORTRAIT_VIDEO],
        pixabay_hits if pixabay_hits is not None else [PIXABAY_PORTRAIT_HIT],
        download_bytes,
    )
    with (
        patch("app.workers.visual_worker.httpx.Client") as mock_cls,
        patch("app.workers.visual_worker.asyncio.run"),
        patch("app.workers.visual_worker._enqueue_compose"),
        patch("app.workers.visual_worker.settings") as mock_settings,
    ):
        mock_cls.return_value.__enter__.return_value = mock_client
        mock_settings.pexels_api_key = pexels_key
        mock_settings.pixabay_api_key = pixabay_key
        mock_settings.media_dir = str(tmp_path)

        result = fetch_visuals.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
        ).get()

    return result, mock_client


def _make_http_status_error(status_code: int) -> httpx_module.HTTPStatusError:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    return httpx_module.HTTPStatusError(
        str(status_code), request=MagicMock(), response=mock_resp
    )


# ── pure: keyword extraction ───────────────────────────────────────────────────


class TestKeywordsForSegment:
    def test_uses_visual_keywords_when_two_or_more_present(self):
        seg = {"visual_keywords": ["technology", "AI robot"], "text": "text", "type": "hook"}
        result = _keywords_for_segment(seg)
        assert "technology" in result and "AI robot" in result

    def test_caps_result_at_three(self):
        seg = {"visual_keywords": ["a", "b", "c", "d", "e"], "text": "", "type": "hook"}
        assert len(_keywords_for_segment(seg)) <= 3

    def test_filters_empty_string_entries(self):
        seg = {"visual_keywords": ["", "technology", "AI"], "text": "", "type": "hook"}
        assert "" not in _keywords_for_segment(seg)

    def test_falls_back_when_fewer_than_two_keywords(self):
        seg = {"visual_keywords": [], "text": "", "type": "hook"}
        result = _keywords_for_segment(seg)
        assert len(result) > 0


# ── pure: clip scoring ─────────────────────────────────────────────────────────


class TestScoreClip:
    def test_portrait_scores_higher_than_landscape(self):
        assert _score_clip(1080, 1920, 10, 10) > _score_clip(1920, 1080, 10, 10)

    def test_exact_duration_match_beats_off_by_ten_seconds(self):
        assert _score_clip(1080, 1920, 10, 10) > _score_clip(1080, 1920, 20, 10)

    def test_higher_resolution_scores_higher(self):
        assert _score_clip(1080, 1920, 10, 10) > _score_clip(480, 854, 10, 10)

    def test_duration_more_than_30s_off_yields_zero_duration_component(self):
        score_far = _score_clip(1080, 1920, 50, 10)
        score_exact = _score_clip(1080, 1920, 10, 10)
        assert score_exact > score_far


# ── pure: Pexels file selection ────────────────────────────────────────────────


class TestBestPexelsFile:
    def test_prefers_portrait_over_landscape(self):
        video = {
            "video_files": [
                {"file_type": "video/mp4", "width": 1920, "height": 1080, "link": "landscape.mp4"},
                {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": "portrait.mp4"},
            ]
        }
        assert _best_pexels_file(video)["link"] == "portrait.mp4"

    def test_picks_highest_resolution_among_portrait(self):
        video = {
            "video_files": [
                {"file_type": "video/mp4", "width": 720,  "height": 1280, "link": "hd720.mp4"},
                {"file_type": "video/mp4", "width": 1080, "height": 1920, "link": "fullhd.mp4"},
            ]
        }
        assert _best_pexels_file(video)["link"] == "fullhd.mp4"

    def test_falls_back_to_landscape_when_no_portrait_available(self):
        video = {
            "video_files": [
                {"file_type": "video/mp4", "width": 1920, "height": 1080, "link": "landscape.mp4"},
            ]
        }
        assert _best_pexels_file(video) is not None

    def test_returns_none_when_no_mp4_files(self):
        video = {"video_files": [{"file_type": "video/webm", "width": 1080, "height": 1920, "link": "x.webm"}]}
        assert _best_pexels_file(video) is None

    def test_returns_none_for_empty_video_files(self):
        assert _best_pexels_file({"video_files": []}) is None


class TestBestPexelsClip:
    def test_returns_none_for_empty_videos_list(self):
        assert _best_pexels_clip([], target_duration=10) is None

    def test_returns_correct_four_tuple(self):
        url, duration, width, height = _best_pexels_clip([PEXELS_PORTRAIT_VIDEO], target_duration=8)
        assert url == "https://player.vimeo.com/pexels_101.mp4"
        assert duration == 8
        assert width == 1080
        assert height == 1920

    def test_portrait_beats_landscape_when_multiple_candidates(self):
        url, *_ = _best_pexels_clip(
            [PEXELS_LANDSCAPE_VIDEO, PEXELS_PORTRAIT_VIDEO], target_duration=10
        )
        assert "101" in url  # portrait clip wins


# ── pure: Pixabay file selection ───────────────────────────────────────────────


class TestBestPixabayFile:
    def test_returns_large_quality_first(self):
        hit = {
            "videos": {
                "large":  {"url": "large.mp4",  "width": 1920, "height": 1080},
                "medium": {"url": "medium.mp4", "width": 1280, "height": 720},
            }
        }
        url, *_ = _best_pixabay_file(hit)
        assert url == "large.mp4"

    def test_falls_back_to_medium_when_large_has_no_url(self):
        hit = {
            "videos": {
                "large":  {},
                "medium": {"url": "medium.mp4", "width": 1280, "height": 720},
            }
        }
        url, *_ = _best_pixabay_file(hit)
        assert url == "medium.mp4"

    def test_returns_none_when_no_videos_key(self):
        assert _best_pixabay_file({}) is None

    def test_returns_none_when_all_qualities_missing_url(self):
        hit = {"videos": {"large": {}, "medium": {}, "small": {}, "tiny": {}}}
        assert _best_pixabay_file(hit) is None


class TestBestPixabayClip:
    def test_returns_none_for_empty_hits_list(self):
        assert _best_pixabay_clip([], target_duration=10) is None

    def test_returns_correct_four_tuple(self):
        url, duration, width, height = _best_pixabay_clip([PIXABAY_PORTRAIT_HIT], target_duration=12)
        assert url == "https://cdn.pixabay.com/pixabay_201.mp4"
        assert duration == 12
        assert width == 1080
        assert height == 1920


# ── task: manifest structure ───────────────────────────────────────────────────


class TestFetchVisualsManifest:
    def test_manifest_file_created(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id)
        assert (tmp_path / video_id / "clips" / "manifest.json").exists()

    def test_manifest_has_one_entry_per_segment(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id)
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        assert len(data) == len(VALID_SCRIPT_JSON["segments"])

    def test_manifest_entries_contain_all_required_keys(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id)
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        for entry in data:
            missing = MANIFEST_REQUIRED_KEYS - entry.keys()
            assert not missing, f"entry {entry['segment_index']} missing keys: {missing}"

    def test_manifest_segment_indices_are_sequential(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id)
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        assert [e["segment_index"] for e in data] == list(range(5))

    def test_manifest_segment_types_match_script_order(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id)
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        expected = [s["type"] for s in VALID_SCRIPT_JSON["segments"]]
        assert [e["segment_type"] for e in data] == expected

    def test_manifest_source_is_pexels_when_pexels_returns_results(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id, pexels_videos=[PEXELS_PORTRAIT_VIDEO], pixabay_key="")
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        assert all(e["source"] == "pexels" for e in data)

    def test_manifest_local_paths_point_to_existing_files(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id)
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        for entry in data:
            assert entry["local_path"] is not None
            assert Path(entry["local_path"]).exists()

    def test_manifest_local_paths_use_segment_index_naming(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id)
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        for entry in data:
            assert Path(entry["local_path"]).name == f"segment_{entry['segment_index']}.mp4"

    def test_manifest_clip_files_contain_download_bytes(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id, download_bytes=FAKE_VIDEO_BYTES)
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        for entry in data:
            assert Path(entry["local_path"]).read_bytes() == FAKE_VIDEO_BYTES

    def test_result_status_is_footage_ready(self, tmp_path):
        result, _ = _run_task(tmp_path, str(uuid.uuid4()))
        assert result["status"] == "footage_ready"

    def test_result_clips_found_equals_segment_count(self, tmp_path):
        result, _ = _run_task(tmp_path, str(uuid.uuid4()))
        assert result["clips_found"] == 5
        assert result["clips_total"] == 5

    def test_result_manifest_path_within_video_clips_dir(self, tmp_path):
        video_id = str(uuid.uuid4())
        result, _ = _run_task(tmp_path, video_id)
        assert video_id in result["manifest_path"]
        assert result["manifest_path"].endswith("manifest.json")

    def test_null_manifest_entry_when_both_apis_return_no_results(self, tmp_path):
        """Pipeline must not crash when no clip is found for a segment."""
        video_id = str(uuid.uuid4())
        result, _ = _run_task(tmp_path, video_id, pexels_videos=[], pixabay_hits=[])
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        for entry in data:
            assert entry["local_path"] is None
            assert entry["source"] is None
        assert result["clips_found"] == 0
        assert result["status"] == "footage_ready"


# ── task: Pixabay fallback ─────────────────────────────────────────────────────


class TestFetchVisualsPixabayFallback:
    """Pixabay must be queried when Pexels returns no usable clip."""

    def test_manifest_source_is_pixabay_when_pexels_returns_empty(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id, pexels_videos=[], pixabay_hits=[PIXABAY_PORTRAIT_HIT])
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        assert all(e["source"] == "pixabay" for e in data)

    def test_pixabay_url_called_when_pexels_returns_empty(self, tmp_path):
        video_id = str(uuid.uuid4())
        _, mock_client = _run_task(
            tmp_path, video_id, pexels_videos=[], pixabay_hits=[PIXABAY_PORTRAIT_HIT]
        )
        pixabay_calls = [c for c in mock_client.get.call_args_list if "pixabay.com" in str(c)]
        assert len(pixabay_calls) > 0

    def test_pixabay_not_called_when_pexels_key_absent(self, tmp_path):
        """With no Pixabay key, Pixabay must never be queried."""
        video_id = str(uuid.uuid4())
        _, mock_client = _run_task(
            tmp_path, video_id, pexels_videos=[PEXELS_PORTRAIT_VIDEO], pixabay_key=""
        )
        pixabay_calls = [c for c in mock_client.get.call_args_list if "pixabay.com" in str(c)]
        assert len(pixabay_calls) == 0

    def test_pexels_not_queried_when_pexels_key_absent(self, tmp_path):
        video_id = str(uuid.uuid4())
        _, mock_client = _run_task(
            tmp_path, video_id, pexels_key="", pixabay_hits=[PIXABAY_PORTRAIT_HIT]
        )
        pexels_calls = [c for c in mock_client.get.call_args_list if "pexels.com" in str(c)]
        assert len(pexels_calls) == 0

    def test_pixabay_used_as_sole_source_when_no_pexels_key(self, tmp_path):
        video_id = str(uuid.uuid4())
        _run_task(tmp_path, video_id, pexels_key="", pixabay_hits=[PIXABAY_PORTRAIT_HIT])
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        assert all(e["source"] == "pixabay" for e in data)

    def test_pexels_preferred_over_pixabay_when_both_available(self, tmp_path):
        """Pexels must win when it returns results, even if Pixabay is also configured."""
        video_id = str(uuid.uuid4())
        _run_task(
            tmp_path, video_id,
            pexels_videos=[PEXELS_PORTRAIT_VIDEO],
            pixabay_hits=[PIXABAY_PORTRAIT_HIT],
        )
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        assert all(e["source"] == "pexels" for e in data)


# ── task: no-key skip ──────────────────────────────────────────────────────────


class TestFetchVisualsSkip:
    """Both API keys absent → status=footage_skipped, pipeline still advances."""

    # Decorator order: bottom → first param after self.
    @patch("app.workers.visual_worker._enqueue_compose")
    @patch("app.workers.visual_worker.asyncio.run")
    @patch("app.workers.visual_worker.settings")
    @patch("app.workers.visual_worker.httpx.Client")
    def test_status_is_footage_skipped(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.pexels_api_key = ""
        mock_settings.pixabay_api_key = ""
        result = fetch_visuals.apply(
            kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
        ).get()
        assert result["status"] == "footage_skipped"

    @patch("app.workers.visual_worker._enqueue_compose")
    @patch("app.workers.visual_worker.asyncio.run")
    @patch("app.workers.visual_worker.settings")
    @patch("app.workers.visual_worker.httpx.Client")
    def test_no_http_calls_when_both_keys_absent(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.pexels_api_key = ""
        mock_settings.pixabay_api_key = ""
        fetch_visuals.apply(
            kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
        ).get()
        mock_httpx_cls.assert_not_called()

    @patch("app.workers.visual_worker._enqueue_compose")
    @patch("app.workers.visual_worker.asyncio.run")
    @patch("app.workers.visual_worker.settings")
    @patch("app.workers.visual_worker.httpx.Client")
    def test_compose_still_enqueued_with_empty_clip_list(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.pexels_api_key = ""
        mock_settings.pixabay_api_key = ""
        video_id = str(uuid.uuid4())
        fetch_visuals.apply(
            kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
        ).get()
        mock_enqueue.assert_called_once_with(video_id, [])

    @patch("app.workers.visual_worker._enqueue_compose")
    @patch("app.workers.visual_worker.asyncio.run")
    @patch("app.workers.visual_worker.settings")
    @patch("app.workers.visual_worker.httpx.Client")
    def test_db_status_updated_when_skipped(
        self, mock_httpx_cls, mock_settings, mock_asyncio_run, mock_enqueue
    ):
        mock_settings.pexels_api_key = ""
        mock_settings.pixabay_api_key = ""
        fetch_visuals.apply(
            kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
        ).get()
        mock_asyncio_run.assert_called_once()


# ── task: retry on 429 and network errors ─────────────────────────────────────


class TestFetchVisualsRetry:
    """429 from either API and download network errors must trigger Celery retry."""

    def _run_with_search_error(self, tmp_path: Path, *, pexels_exc=None, pixabay_exc=None) -> None:
        mock_client = MagicMock()

        def _get(url, *args, **kwargs):
            if "pexels.com" in str(url) and pexels_exc:
                raise pexels_exc
            if "pixabay.com" in str(url) and pixabay_exc:
                raise pixabay_exc
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"videos": [], "hits": []}
            return resp

        mock_client.get.side_effect = _get

        with (
            patch("app.workers.visual_worker.httpx.Client") as mock_cls,
            patch("app.workers.visual_worker.asyncio.run"),
            patch("app.workers.visual_worker._enqueue_compose"),
            patch("app.workers.visual_worker.settings") as mock_settings,
        ):
            mock_cls.return_value.__enter__.return_value = mock_client
            mock_settings.pexels_api_key = "pexels-key"
            mock_settings.pixabay_api_key = "pixabay-key"
            mock_settings.media_dir = str(tmp_path)
            fetch_visuals.apply(
                kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
            ).get()

    def test_pexels_429_raises_after_max_retries(self, tmp_path):
        with pytest.raises(Exception):
            self._run_with_search_error(tmp_path, pexels_exc=_make_http_status_error(429))

    def test_pixabay_429_raises_after_max_retries(self, tmp_path):
        with pytest.raises(Exception):
            self._run_with_search_error(tmp_path, pixabay_exc=_make_http_status_error(429))

    def test_non_429_pexels_error_is_logged_and_pixabay_tried(self, tmp_path):
        """A non-rate-limit Pexels error should not abort — Pixabay fallback is tried."""
        video_id = str(uuid.uuid4())
        mock_client = MagicMock()

        def _get(url, *args, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if "pexels.com" in str(url):
                raise _make_http_status_error(500)
            resp.json.return_value = {"hits": [PIXABAY_PORTRAIT_HIT]}
            return resp

        mock_client.get.side_effect = _get
        stream_resp = MagicMock()
        stream_resp.raise_for_status = MagicMock()
        stream_resp.iter_bytes.return_value = iter([FAKE_VIDEO_BYTES])
        stream_cm = mock_client.stream.return_value
        stream_cm.__enter__.return_value = stream_resp
        stream_cm.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.workers.visual_worker.httpx.Client") as mock_cls,
            patch("app.workers.visual_worker.asyncio.run"),
            patch("app.workers.visual_worker._enqueue_compose"),
            patch("app.workers.visual_worker.settings") as mock_settings,
        ):
            mock_cls.return_value.__enter__.return_value = mock_client
            mock_settings.pexels_api_key = "pexels-key"
            mock_settings.pixabay_api_key = "pixabay-key"
            mock_settings.media_dir = str(tmp_path)

            result = fetch_visuals.apply(
                kwargs={"video_id": video_id, "script_json": VALID_SCRIPT_JSON}
            ).get()

        # Task completes; clips came from Pixabay
        data = json.loads((tmp_path / video_id / "clips" / "manifest.json").read_text())
        assert all(e["source"] == "pixabay" for e in data)
        assert result["status"] == "footage_ready"

    def test_download_connection_error_raises_after_max_retries(self, tmp_path):
        """A network error during clip download must trigger retry and eventually fail."""
        mock_client = MagicMock()

        def _get(url, *args, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {"videos": [PEXELS_PORTRAIT_VIDEO]}
            return resp

        mock_client.get.side_effect = _get
        mock_client.stream.side_effect = httpx_module.ConnectError("connection refused")

        with (
            patch("app.workers.visual_worker.httpx.Client") as mock_cls,
            patch("app.workers.visual_worker.asyncio.run"),
            patch("app.workers.visual_worker._enqueue_compose"),
            patch("app.workers.visual_worker.settings") as mock_settings,
        ):
            mock_cls.return_value.__enter__.return_value = mock_client
            mock_settings.pexels_api_key = "pexels-key"
            mock_settings.pixabay_api_key = ""
            mock_settings.media_dir = str(tmp_path)

            with pytest.raises(Exception):
                fetch_visuals.apply(
                    kwargs={"video_id": str(uuid.uuid4()), "script_json": VALID_SCRIPT_JSON}
                ).get()

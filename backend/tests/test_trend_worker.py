"""Tests for trend_worker — all external calls mocked."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.workers.trend_worker import (
    OPPORTUNITY_THRESHOLD,
    _clamp,
    _log_normalize,
    _monetization_score,
    _opportunity,
    _scrape_google_trends,
    _scrape_reddit,
    scrape_trends,
)


# ── pure-function tests ────────────────────────────────────────────────────────


class TestHelpers:
    def test_clamp_bounds(self):
        assert _clamp(-10) == 0.0
        assert _clamp(150) == 100.0
        assert _clamp(50) == 50.0

    def test_log_normalize_zero(self):
        assert _log_normalize(0, 1000) == 0.0

    def test_log_normalize_at_scale(self):
        assert _log_normalize(1000, 1000) == pytest.approx(100.0, abs=1e-6)

    def test_log_normalize_above_scale_clamped(self):
        assert _log_normalize(2000, 1000) == 100.0

    def test_monetization_known_niche(self):
        assert _monetization_score("AI tools") == 85.0
        assert _monetization_score("finance tips") == 90.0

    def test_monetization_unknown_niche_returns_default(self):
        assert _monetization_score("knitting") == 55.0

    def test_opportunity_formula(self):
        score = _opportunity(virality=80, engagement=70, monetization=85, saturation=20)
        expected = 0.40 * 80 + 0.25 * 70 + 0.20 * 85 - 0.15 * 20
        assert score == pytest.approx(expected)

    def test_opportunity_above_threshold_when_strong(self):
        score = _opportunity(virality=90, engagement=80, monetization=85, saturation=10)
        assert score >= OPPORTUNITY_THRESHOLD


# ── Google Trends ──────────────────────────────────────────────────────────────


def _make_iot_df(keywords: list[str], values: list[list[int]]) -> pd.DataFrame:
    import numpy as np

    data = {kw: vals for kw, vals in zip(keywords, values)}
    data["isPartial"] = [False] * len(values[0])
    return pd.DataFrame(data)


class TestScrapeGoogleTrends:
    @patch("app.workers.trend_worker.TrendReq")
    def test_returns_signal_for_keyword(self, mock_trendrq):
        pt = MagicMock()
        mock_trendrq.return_value = pt
        pt.interest_over_time.return_value = _make_iot_df(
            ["AI tools"], [[60, 65, 70, 68, 72, 75, 80]]
        )
        pt.related_queries.return_value = {
            "AI tools": {"top": None, "rising": pd.DataFrame({"query": ["a", "b", "c"]})}
        }

        signals = _scrape_google_trends("ai", ["AI tools"])

        assert len(signals) == 1
        sig = signals[0]
        assert sig["source"] == "google_trends"
        assert sig["niche"] == "ai"
        assert sig["topic"] == "AI tools"
        assert 0 <= sig["virality_score"] <= 100
        assert 0 <= sig["opportunity_score"] <= 100
        assert sig["velocity"] > 0  # series is rising

    @patch("app.workers.trend_worker.TrendReq")
    def test_skips_zero_interest_keyword(self, mock_trendrq):
        pt = MagicMock()
        mock_trendrq.return_value = pt
        pt.interest_over_time.return_value = _make_iot_df(
            ["dead topic"], [[0, 0, 0, 0, 0, 0, 0]]
        )
        pt.related_queries.return_value = {"dead topic": {"top": None, "rising": None}}

        signals = _scrape_google_trends("tech", ["dead topic"])

        assert signals == []

    @patch("app.workers.trend_worker.TrendReq")
    def test_rate_limit_returns_empty(self, mock_trendrq):
        from pytrends.exceptions import ResponseError

        pt = MagicMock()
        mock_trendrq.return_value = pt
        pt.build_payload.side_effect = ResponseError("429", None)

        signals = _scrape_google_trends("ai", ["AI tools"])

        assert signals == []


# ── Reddit ─────────────────────────────────────────────────────────────────────


def _make_post(
    title: str,
    score: int = 5000,
    num_comments: int = 200,
    upvote_ratio: float = 0.92,
    created_utc: float | None = None,
    stickied: bool = False,
) -> MagicMock:
    import time

    post = MagicMock()
    post.title = title
    post.score = score
    post.num_comments = num_comments
    post.upvote_ratio = upvote_ratio
    post.created_utc = created_utc or (time.time() - 3600)  # 1 h ago by default
    post.stickied = stickied
    post.id = "abc123"
    post.permalink = "/r/technology/abc123"
    return post


class TestScrapeReddit:
    @patch("app.workers.trend_worker.settings")
    @patch("app.workers.trend_worker.praw.Reddit")
    def test_returns_signals_for_subreddit(self, mock_reddit_cls, mock_settings):
        mock_settings.reddit_client_id = "cid"
        mock_settings.reddit_client_secret = "csec"

        mock_reddit = MagicMock()
        mock_reddit_cls.return_value = mock_reddit

        sub = MagicMock()
        mock_reddit.subreddit.return_value = sub
        sub.hot.return_value = [_make_post("AI beats human at chess")]

        signals = _scrape_reddit("ai", ["technology"])

        assert len(signals) == 1
        sig = signals[0]
        assert sig["source"] == "reddit/technology"
        assert sig["niche"] == "ai"
        assert sig["topic"] == "AI beats human at chess"
        assert 0 <= sig["virality_score"] <= 100
        assert sig["saturation_score"] < 50  # 1 h old — not saturated

    @patch("app.workers.trend_worker.settings")
    def test_skips_when_no_credentials(self, mock_settings):
        mock_settings.reddit_client_id = ""
        mock_settings.reddit_client_secret = ""

        signals = _scrape_reddit("ai", ["technology"])

        assert signals == []

    @patch("app.workers.trend_worker.settings")
    @patch("app.workers.trend_worker.praw.Reddit")
    def test_stickied_posts_excluded(self, mock_reddit_cls, mock_settings):
        mock_settings.reddit_client_id = "cid"
        mock_settings.reddit_client_secret = "csec"

        mock_reddit = MagicMock()
        mock_reddit_cls.return_value = mock_reddit
        sub = MagicMock()
        mock_reddit.subreddit.return_value = sub
        sub.hot.return_value = [_make_post("Pinned announcement", stickied=True)]

        signals = _scrape_reddit("tech", ["technology"])

        assert signals == []

    @patch("app.workers.trend_worker.settings")
    @patch("app.workers.trend_worker.praw.Reddit")
    def test_missing_subreddit_skipped_gracefully(self, mock_reddit_cls, mock_settings):
        import prawcore.exceptions

        mock_settings.reddit_client_id = "cid"
        mock_settings.reddit_client_secret = "csec"

        mock_reddit = MagicMock()
        mock_reddit_cls.return_value = mock_reddit
        sub = MagicMock()
        mock_reddit.subreddit.return_value = sub
        sub.hot.side_effect = prawcore.exceptions.NotFound(MagicMock())

        signals = _scrape_reddit("tech", ["nonexistentsubreddit"])

        assert signals == []


# ── task-level integration ─────────────────────────────────────────────────────


class TestScrapeTask:
    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_task_returns_summary(self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs):
        video_id = "vid-001"
        trend_signal_id = "ts-001"
        qualifying_signal = {
            "source": "google_trends",
            "niche": "ai",
            "topic": "AI goes viral",
            "virality_score": 90.0,
            "engagement_score": 80.0,
            "monetization_score": 85.0,
            "saturation_score": 10.0,
            "opportunity_score": 80.5,
            "velocity": 30.0,
            "raw_data": "{}",
        }
        mock_gt.return_value = [qualifying_signal]
        mock_reddit.return_value = []
        # _save_and_enqueue now returns (pipeline_jobs, skipped)
        mock_asyncio_run.return_value = (
            [{"video_id": video_id, "topic": "AI goes viral", "niche": "ai", "trend_signal_id": trend_signal_id}],
            0,
        )

        result = scrape_trends.apply(kwargs={"niche": "ai"}).get()

        assert result["niche"] == "ai"
        assert result["total_scraped"] == 1
        assert result["qualifying"] == 1
        assert result["saved"] == 1
        assert result["enqueued"] == 1
        assert result["skipped_duplicates"] == 0
        mock_gs.apply_async.assert_called_once()

    @patch("app.workers.trend_worker.generate_script")
    @patch("app.workers.trend_worker.asyncio.run")
    @patch("app.workers.trend_worker._scrape_reddit")
    @patch("app.workers.trend_worker._scrape_google_trends")
    def test_below_threshold_signals_not_saved(self, mock_gt, mock_reddit, mock_asyncio_run, mock_gs):
        low_signal = {
            "source": "google_trends",
            "niche": "ai",
            "topic": "weak trend",
            "virality_score": 20.0,
            "engagement_score": 30.0,
            "monetization_score": 50.0,
            "saturation_score": 80.0,
            "opportunity_score": 14.0,  # below threshold
            "velocity": 0.0,
            "raw_data": "{}",
        }
        mock_gt.return_value = [low_signal]
        mock_reddit.return_value = []
        mock_asyncio_run.return_value = ([], 0)

        result = scrape_trends.apply(kwargs={"niche": "ai"}).get()

        assert result["qualifying"] == 0
        assert result["saved"] == 0
        assert result["enqueued"] == 0
        mock_gs.apply_async.assert_not_called()

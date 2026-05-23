"""Trend scraper worker — Google Trends (pytrends) + Reddit (PRAW) → trend_signals table."""

import asyncio
import json
import logging
import math
import time
from datetime import UTC, datetime, timedelta

import praw
import prawcore.exceptions
from pytrends.exceptions import ResponseError
from pytrends.request import TrendReq
from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import async_session_factory
from app.models.trend_signal import TrendSignal

logger = logging.getLogger(__name__)

# ── constants ────────────────────────────────────────────────────────────────

OPPORTUNITY_THRESHOLD = 70.0
DEDUP_WINDOW_HOURS = 6

# Per-niche seed keywords used when the caller provides none.
NICHE_KEYWORDS: dict[str, list[str]] = {
    "ai": ["AI tools", "ChatGPT tips", "artificial intelligence 2024", "AI news"],
    "technology": ["tech news 2024", "best apps 2024", "new gadgets"],
    "finance": ["make money online", "passive income ideas", "investing tips 2024"],
    "gaming": ["gaming news", "best games 2024", "game tips"],
    "health": ["health tips 2024", "fitness routine", "wellness trends"],
    "entertainment": ["viral videos 2024", "trending content", "internet culture"],
    "videos": ["viral YouTube shorts", "trending shorts", "YouTube tips 2024"],
}

# Default subreddits per source-type (overridable by caller).
DEFAULT_SUBREDDITS = ["technology", "artificial", "videos"]

# Monetization baseline score per niche keyword (0–100).
_MONETIZATION_TABLE: dict[str, float] = {
    "finance": 90.0,
    "investing": 90.0,
    "crypto": 85.0,
    "money": 85.0,
    "ai": 85.0,
    "artificial intelligence": 85.0,
    "business": 80.0,
    "marketing": 80.0,
    "health": 80.0,
    "technology": 75.0,
    "tech": 75.0,
    "education": 75.0,
    "science": 70.0,
    "travel": 70.0,
    "fitness": 70.0,
    "gaming": 65.0,
    "sports": 65.0,
    "entertainment": 60.0,
    "food": 60.0,
    "videos": 60.0,
}


# ── helpers ───────────────────────────────────────────────────────────────────


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _log_normalize(value: float, scale: float) -> float:
    """Map [0, scale] → [0, 100] using log1p so outliers don't dominate."""
    if value <= 0 or scale <= 0:
        return 0.0
    return _clamp(math.log1p(value) / math.log1p(scale) * 100.0)


def _monetization_score(niche: str) -> float:
    niche_lower = niche.lower()
    for key, score in _MONETIZATION_TABLE.items():
        if key in niche_lower:
            return score
    return 55.0


def _opportunity(virality: float, engagement: float, monetization: float, saturation: float) -> float:
    """Score = 0.40×V + 0.25×E + 0.20×M − 0.15×S  (all inputs 0–100)."""
    return 0.40 * virality + 0.25 * engagement + 0.20 * monetization - 0.15 * saturation


# ── Google Trends ──────────────────────────────────────────────────────────────


def _scrape_google_trends(niche: str, keywords: list[str]) -> list[dict]:
    """Return scored signal dicts for each keyword with Google Trends data."""
    try:
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=2, backoff_factor=0.2)
    except Exception as exc:
        logger.error("pytrends init failed: %s", exc)
        return []

    signals: list[dict] = []

    # Google Trends accepts at most 5 keywords per request.
    for i in range(0, len(keywords), 5):
        batch = keywords[i : i + 5]
        try:
            pt.build_payload(kw_list=batch, cat=0, timeframe="now 7-d", geo="US")
            iot = pt.interest_over_time()
            related = pt.related_queries()
        except ResponseError as exc:
            logger.warning("Google Trends rate-limited (batch %d): %s", i, exc)
            break
        except Exception as exc:
            logger.error("Google Trends fetch error (batch %d): %s", i, exc)
            break

        # Drop the helper column Trends appends.
        if not iot.empty and "isPartial" in iot.columns:
            iot = iot.drop(columns=["isPartial"])

        for kw in batch:
            if iot.empty or kw not in iot.columns:
                continue

            series = iot[kw].astype(float).values
            if series.max() == 0:
                continue  # Trend has zero interest — skip.

            virality_score = _clamp(float(series.mean()))

            # Velocity: pct change first→last, normalised to [−100, 100].
            if len(series) >= 2 and series[0] > 0:
                raw_vel = (series[-1] - series[0]) / series[0] * 100.0
                velocity = _clamp(raw_vel, -100.0, 100.0)
            else:
                velocity = 0.0

            # Engagement proxy: rising related-query count.
            rising_count = 0
            kw_related = related.get(kw, {})
            if kw_related and kw_related.get("rising") is not None:
                rising_count = len(kw_related["rising"])
            engagement_score = _clamp(40.0 + (rising_count / 25.0) * 60.0)

            monetization_score = _monetization_score(niche)

            # Saturation: fraction of days the topic was above 50 (persistent = saturated).
            above_50_frac = float((series > 50).sum()) / max(len(series), 1)
            saturation_score = _clamp(above_50_frac * 80.0)

            opportunity_score = _clamp(
                _opportunity(virality_score, engagement_score, monetization_score, saturation_score)
            )

            signals.append(
                {
                    "source": "google_trends",
                    "niche": niche,
                    "topic": kw,
                    "virality_score": virality_score,
                    "engagement_score": engagement_score,
                    "monetization_score": monetization_score,
                    "saturation_score": saturation_score,
                    "opportunity_score": opportunity_score,
                    "velocity": velocity,
                    "raw_data": json.dumps({"interest_series": series.tolist()}),
                }
            )

        # Polite delay between batches to avoid rate-limiting.
        if i + 5 < len(keywords):
            time.sleep(3)

    logger.debug("google_trends scraped %d signals for niche=%r", len(signals), niche)
    return signals


# ── Reddit ─────────────────────────────────────────────────────────────────────


def _build_reddit_client() -> praw.Reddit | None:
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        logger.info("Reddit credentials not set — skipping Reddit scrape")
        return None
    try:
        reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent="shortform-os/0.1 (by u/shortform_os_bot)",
        )
        reddit.read_only = True
        return reddit
    except Exception as exc:
        logger.error("PRAW client init failed: %s", exc)
        return None


def _scrape_reddit(niche: str, subreddits: list[str], post_limit: int = 50) -> list[dict]:
    reddit = _build_reddit_client()
    if reddit is None:
        return []

    monetization_score = _monetization_score(niche)
    now = datetime.now(UTC)
    signals: list[dict] = []

    for sub_name in subreddits:
        try:
            sub = reddit.subreddit(sub_name)
            posts = [p for p in sub.hot(limit=post_limit) if not p.stickied]
        except prawcore.exceptions.NotFound:
            logger.warning("Subreddit r/%s not found — skipping", sub_name)
            continue
        except prawcore.exceptions.Forbidden:
            logger.warning("Subreddit r/%s is private — skipping", sub_name)
            continue
        except Exception as exc:
            logger.warning("Reddit fetch failed for r/%s: %s", sub_name, exc)
            continue

        if not posts:
            continue

        max_score = max((p.score for p in posts), default=1) or 1
        max_comments = max((p.num_comments for p in posts), default=1) or 1

        for post in posts:
            virality_score = _log_normalize(post.score, max_score * 2.0)

            comments_norm = _log_normalize(post.num_comments, max_comments * 2.0)
            engagement_score = _clamp(post.upvote_ratio * 50.0 + comments_norm * 50.0)

            # Posts ≤2 h old have near-zero saturation; 48 h+ ≈ 70.
            age_hours = (
                now - datetime.fromtimestamp(post.created_utc, tz=UTC)
            ).total_seconds() / 3600.0
            saturation_score = _clamp(age_hours / 48.0 * 70.0)

            # Velocity: upvote_ratio above 0.5 means it's still climbing.
            velocity = _clamp((post.upvote_ratio - 0.5) * 200.0)

            opportunity_score = _clamp(
                _opportunity(virality_score, engagement_score, monetization_score, saturation_score)
            )

            signals.append(
                {
                    "source": f"reddit/{sub_name}",
                    "niche": niche,
                    "topic": post.title,
                    "virality_score": virality_score,
                    "engagement_score": engagement_score,
                    "monetization_score": monetization_score,
                    "saturation_score": saturation_score,
                    "opportunity_score": opportunity_score,
                    "velocity": velocity,
                    "raw_data": json.dumps(
                        {
                            "post_id": post.id,
                            "score": post.score,
                            "num_comments": post.num_comments,
                            "upvote_ratio": post.upvote_ratio,
                            "created_utc": post.created_utc,
                            "url": f"https://reddit.com{post.permalink}",
                        }
                    ),
                }
            )

    logger.debug("reddit scraped %d signals for niche=%r", len(signals), niche)
    return signals


# ── DB helpers (async, called via asyncio.run) ────────────────────────────────


async def _filter_and_save(candidates: list[dict], niche: str) -> tuple[int, int]:
    """Dedup against a 6-hour window, insert qualifying signals. Returns (saved, skipped)."""
    if not candidates:
        return 0, 0

    cutoff = datetime.now(UTC) - timedelta(hours=DEDUP_WINDOW_HOURS)

    async with async_session_factory() as session:
        result = await session.execute(
            select(TrendSignal.topic).where(
                TrendSignal.niche == niche,
                TrendSignal.created_at >= cutoff,
            )
        )
        existing_topics: set[str] = {row[0] for row in result}

        fresh = [s for s in candidates if s["topic"] not in existing_topics]
        skipped = len(candidates) - len(fresh)

        for data in fresh:
            session.add(TrendSignal(**data))
        await session.commit()

    return len(fresh), skipped


# ── Celery task ───────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.workers.trend_worker.scrape_trends",
    queue="trend",
    max_retries=3,
    default_retry_delay=60,
)
def scrape_trends(
    self,
    niche: str,
    keywords: list[str] | None = None,
    subreddits: list[str] | None = None,
) -> dict:
    """Scrape Google Trends + Reddit for *niche*, score signals, persist qualifying rows.

    Idempotent: duplicate topics within a 6-hour window are silently skipped.
    """
    logger.info(
        "scrape_trends started task_id=%s niche=%r keywords=%s subreddits=%s",
        self.request.id,
        niche,
        keywords,
        subreddits,
    )

    attempt = self.request.retries
    backoff = 60 * (2**attempt)

    effective_keywords = keywords or NICHE_KEYWORDS.get(
        niche.lower(), [f"{niche} trends", f"{niche} viral content"]
    )
    effective_subreddits = subreddits or DEFAULT_SUBREDDITS

    try:
        gt_signals = _scrape_google_trends(niche, effective_keywords)

        # Courtesy delay between the two external services.
        time.sleep(2)

        reddit_signals = _scrape_reddit(niche, effective_subreddits)

    except Exception as exc:
        logger.error(
            "scrape_trends fetch phase failed attempt=%d: %s", attempt, exc
        )
        raise self.retry(exc=exc, countdown=backoff)

    all_signals = gt_signals + reddit_signals
    qualifying = [s for s in all_signals if s["opportunity_score"] >= OPPORTUNITY_THRESHOLD]

    try:
        saved, skipped = asyncio.run(_filter_and_save(qualifying, niche))
    except Exception as exc:
        logger.error(
            "scrape_trends DB phase failed attempt=%d: %s", attempt, exc
        )
        raise self.retry(exc=exc, countdown=backoff)

    result = {
        "niche": niche,
        "total_scraped": len(all_signals),
        "gt_signals": len(gt_signals),
        "reddit_signals": len(reddit_signals),
        "qualifying": len(qualifying),
        "saved": saved,
        "skipped_duplicates": skipped,
    }

    logger.info(
        "scrape_trends completed task_id=%s niche=%r %s",
        self.request.id,
        niche,
        result,
    )
    return result

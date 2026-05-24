"""Visual fetch worker — Pexels + Pixabay stock footage download."""

import asyncio
import json
import logging
import uuid
from pathlib import Path
from typing import TypedDict

import httpx
from celery import Task

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import async_session_factory
from app.models.video import Video

logger = logging.getLogger(__name__)

PEXELS_BASE = "https://api.pexels.com"
PIXABAY_BASE = "https://pixabay.com/api"

# Generous read timeout for large clip downloads; short timeout for API searches.
_SEARCH_TIMEOUT = httpx.Timeout(30.0)
_DOWNLOAD_TIMEOUT = httpx.Timeout(30.0, read=300.0)


class ClipMeta(TypedDict):
    segment_index: int
    segment_type: str
    local_path: str | None
    url: str | None
    duration: int | None
    width: int | None
    height: int | None
    source: str | None  # "pexels" | "pixabay" | None


# ── keyword extraction ─────────────────────────────────────────────────────────


def _keywords_for_segment(segment: dict) -> list[str]:
    """Return 2–3 search keywords for a segment.

    Uses visual_keywords from the script first (LLM-generated, purpose-built).
    Falls back to RAKE noun-phrase extraction from segment text if needed.
    """
    vk: list[str] = [k for k in (segment.get("visual_keywords") or []) if k]
    if len(vk) >= 2:
        return vk[:3]

    try:
        import nltk
        from rake_nltk import Rake

        nltk.download("stopwords", quiet=True)
        nltk.download("punkt_tab", quiet=True)
        r = Rake(min_length=1, max_length=3)
        r.extract_keywords_from_text(segment.get("text", ""))
        extracted = r.get_ranked_phrases()[:3]
        combined = vk + [p for p in extracted if p not in vk]
        return combined[:3] if combined else vk
    except Exception as exc:
        logger.debug("RAKE extraction failed: %s", exc)

    return vk or [segment.get("type", "aerial nature")]


# ── clip scoring ───────────────────────────────────────────────────────────────


def _score_clip(width: int, height: int, duration: int, target_duration: int) -> float:
    """Score a clip candidate — higher is better.

    Portrait orientation is heavily preferred (9:16 target).
    Duration fit dominates over resolution.
    """
    portrait_bonus = 100.0 if height > width else 0.0
    # Up to 30 pts for matching target duration; drops 1 pt per second off.
    duration_fit = max(0.0, 30.0 - abs(duration - target_duration))
    # Up to 20 pts for resolution, normalised to 1080×1920 native.
    resolution_bonus = min((width * height) / (1080.0 * 1920.0), 1.0) * 20.0
    return portrait_bonus + duration_fit + resolution_bonus


# ── Pexels ─────────────────────────────────────────────────────────────────────


def _best_pexels_file(video: dict) -> dict | None:
    """Pick the best video_file entry from a Pexels video object.

    Prefers portrait MP4 files, then highest resolution.
    """
    files = [
        f for f in video.get("video_files", [])
        if f.get("file_type") == "video/mp4" and f.get("link")
    ]
    if not files:
        return None
    portrait = [f for f in files if (f.get("height") or 0) > (f.get("width") or 0)]
    pool = portrait if portrait else files
    return max(pool, key=lambda f: (f.get("width") or 0) * (f.get("height") or 0))


def _best_pexels_clip(
    videos: list[dict],
    target_duration: int,
) -> tuple[str, int, int, int] | None:
    """Return (url, duration, width, height) for the highest-scoring Pexels video."""
    best_score = -1.0
    best: tuple[str, int, int, int] | None = None
    for video in videos:
        duration = video.get("duration") or 0
        vf = _best_pexels_file(video)
        if not vf:
            continue
        w, h = vf.get("width") or 0, vf.get("height") or 0
        score = _score_clip(w, h, duration, target_duration)
        if score > best_score:
            best_score = score
            best = (vf["link"], duration, w, h)
    return best


def _search_pexels(
    query: str,
    target_duration: int,
    client: httpx.Client,
) -> tuple[str, int, int, int] | None:
    resp = client.get(
        f"{PEXELS_BASE}/videos/search",
        headers={"Authorization": settings.pexels_api_key},
        params={"query": query, "orientation": "portrait", "per_page": 5},
        timeout=_SEARCH_TIMEOUT,
    )
    resp.raise_for_status()
    return _best_pexels_clip(resp.json().get("videos", []), target_duration)


# ── Pixabay ────────────────────────────────────────────────────────────────────


def _best_pixabay_file(hit: dict) -> tuple[str, int, int] | None:
    """Return (url, width, height) for the best quality file in a Pixabay hit."""
    videos = hit.get("videos") or {}
    for quality in ("large", "medium", "small", "tiny"):
        entry = videos.get(quality)
        if entry and entry.get("url"):
            return entry["url"], entry.get("width") or 0, entry.get("height") or 0
    return None


def _best_pixabay_clip(
    hits: list[dict],
    target_duration: int,
) -> tuple[str, int, int, int] | None:
    """Return (url, duration, width, height) for the highest-scoring Pixabay hit."""
    best_score = -1.0
    best: tuple[str, int, int, int] | None = None
    for hit in hits:
        duration = hit.get("duration") or 0
        file_info = _best_pixabay_file(hit)
        if not file_info:
            continue
        url, w, h = file_info
        score = _score_clip(w, h, duration, target_duration)
        if score > best_score:
            best_score = score
            best = (url, duration, w, h)
    return best


def _search_pixabay(
    query: str,
    target_duration: int,
    client: httpx.Client,
) -> tuple[str, int, int, int] | None:
    resp = client.get(
        f"{PIXABAY_BASE}/videos/",
        params={
            "key": settings.pixabay_api_key,
            "q": query,
            "video_type": "film",
            "orientation": "vertical",
            "per_page": 5,
        },
        timeout=_SEARCH_TIMEOUT,
    )
    resp.raise_for_status()
    return _best_pixabay_clip(resp.json().get("hits", []), target_duration)


# ── download ───────────────────────────────────────────────────────────────────


def _download_clip(url: str, dest: Path, client: httpx.Client) -> None:
    """Stream a video file to *dest* in 64 KB chunks."""
    with client.stream("GET", url, follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=65536):
                fh.write(chunk)


# ── DB helper ──────────────────────────────────────────────────────────────────


async def _update_video_status(video_id: str, status: str) -> None:
    async with async_session_factory() as session:
        video = await session.get(Video, uuid.UUID(video_id))
        if video is not None:
            video.status = status
        await session.commit()


# ── Celery task ────────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.workers.visual_worker.fetch_visuals",
    queue="script",
    max_retries=3,
    default_retry_delay=60,
)
def fetch_visuals(self: Task, video_id: str, script_json: dict) -> dict:
    """Fetch stock footage for each of the 5 script segments.

    Steps:
      1. Derive search keywords from each segment's visual_keywords field.
      2. Search Pexels (portrait); fall back to Pixabay (vertical) if < 2 results.
      3. Download the best clip per segment → MEDIA_DIR/{video_id}/clips/segment_{i}.mp4.
      4. Write MEDIA_DIR/{video_id}/clips/manifest.json with per-clip metadata.
      5. Advance Video status → footage_ready (or footage_skipped).
      6. Enqueue compose_video.
    """
    logger.info(
        "fetch_visuals started task_id=%s video_id=%s",
        self.request.id,
        video_id,
    )

    attempt = self.request.retries
    backoff = 60 * (2**attempt)

    # ── 0. skip if both API keys are absent ────────────────────────────────────
    if not settings.pexels_api_key and not settings.pixabay_api_key:
        logger.warning(
            "fetch_visuals skipped task_id=%s video_id=%s reason=no_api_keys",
            self.request.id,
            video_id,
        )
        asyncio.run(_update_video_status(video_id, "footage_skipped"))
        _enqueue_compose(video_id, [])
        return {"status": "footage_skipped", "video_id": video_id}

    segments: list[dict] = script_json.get("segments", [])
    clips_dir = Path(settings.media_dir) / video_id / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[ClipMeta] = []

    # ── 1–3. fetch and download one clip per segment ───────────────────────────
    try:
        with httpx.Client() as client:
            for idx, segment in enumerate(segments):
                target_duration = (
                    (segment.get("end_sec") or 0) - (segment.get("start_sec") or 0)
                )
                keywords = _keywords_for_segment(segment)
                # Two keywords gives better recall than three on stock APIs.
                query = " ".join(keywords[:2])

                clip: tuple[str, int, int, int] | None = None
                source = ""

                # ── Pexels first ───────────────────────────────────────────────
                if settings.pexels_api_key:
                    try:
                        clip = _search_pexels(query, target_duration, client)
                        if clip:
                            source = "pexels"
                        else:
                            logger.debug(
                                "fetch_visuals pexels 0 results segment=%d query=%r",
                                idx, query,
                            )
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 429:
                            logger.warning(
                                "fetch_visuals pexels rate-limited segment=%d attempt=%d",
                                idx, attempt,
                            )
                            raise self.retry(exc=exc, countdown=backoff * 2)
                        logger.warning(
                            "fetch_visuals pexels HTTP %d segment=%d: %s",
                            exc.response.status_code, idx, exc,
                        )

                # ── Pixabay fallback ───────────────────────────────────────────
                if clip is None and settings.pixabay_api_key:
                    try:
                        clip = _search_pixabay(query, target_duration, client)
                        if clip:
                            source = "pixabay"
                        else:
                            logger.debug(
                                "fetch_visuals pixabay 0 results segment=%d query=%r",
                                idx, query,
                            )
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 429:
                            logger.warning(
                                "fetch_visuals pixabay rate-limited segment=%d attempt=%d",
                                idx, attempt,
                            )
                            raise self.retry(exc=exc, countdown=backoff * 2)
                        logger.warning(
                            "fetch_visuals pixabay HTTP %d segment=%d: %s",
                            exc.response.status_code, idx, exc,
                        )

                # ── no clip found — store null entry and continue ──────────────
                if clip is None:
                    logger.warning(
                        "fetch_visuals no clip found segment=%d query=%r; "
                        "manifest entry will be null",
                        idx, query,
                    )
                    manifest.append(
                        ClipMeta(
                            segment_index=idx,
                            segment_type=segment.get("type", ""),
                            local_path=None,
                            url=None,
                            duration=None,
                            width=None,
                            height=None,
                            source=None,
                        )
                    )
                    continue

                url, duration, width, height = clip
                dest = clips_dir / f"segment_{idx}.mp4"

                try:
                    _download_clip(url, dest, client)
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 429:
                        raise self.retry(exc=exc, countdown=backoff * 2)
                    raise self.retry(exc=exc, countdown=backoff)
                except httpx.RequestError as exc:
                    raise self.retry(exc=exc, countdown=backoff)

                manifest.append(
                    ClipMeta(
                        segment_index=idx,
                        segment_type=segment.get("type", ""),
                        local_path=str(dest),
                        url=url,
                        duration=duration,
                        width=width,
                        height=height,
                        source=source,
                    )
                )
                logger.debug(
                    "fetch_visuals downloaded segment=%d file=%s source=%s",
                    idx, dest.name, source,
                )

    except httpx.RequestError as exc:
        logger.error("fetch_visuals network error attempt=%d: %s", attempt, exc)
        raise self.retry(exc=exc, countdown=backoff)

    # ── 4. write manifest ──────────────────────────────────────────────────────
    manifest_path = clips_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # ── 5. update DB status ────────────────────────────────────────────────────
    try:
        asyncio.run(_update_video_status(video_id, "footage_ready"))
    except Exception as exc:
        logger.error("fetch_visuals DB update failed attempt=%d: %s", attempt, exc)
        raise self.retry(exc=exc, countdown=backoff)

    # ── 6. enqueue composition ─────────────────────────────────────────────────
    clip_paths = [m["local_path"] for m in manifest if m.get("local_path")]
    _enqueue_compose(video_id, clip_paths)

    clips_found = len(clip_paths)
    logger.info(
        "fetch_visuals completed task_id=%s video_id=%s clips=%d/%d",
        self.request.id, video_id, clips_found, len(segments),
    )
    return {
        "status": "footage_ready",
        "video_id": video_id,
        "manifest_path": str(manifest_path),
        "clips_found": clips_found,
        "clips_total": len(segments),
    }


def _enqueue_compose(video_id: str, clip_paths: list[str]) -> None:
    from app.workers.compose_worker import compose_video

    audio_path = str(Path(settings.media_dir) / video_id / "narration.mp3")
    compose_video.apply_async(
        kwargs={
            "video_id": video_id,
            "audio_path": audio_path,
            "clips": clip_paths,
        }
    )

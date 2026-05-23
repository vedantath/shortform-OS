"""Voice synthesis worker — ElevenLabs TTS → narration.mp3 + timestamps.json."""

import asyncio
import json
import logging
import uuid
from pathlib import Path

import httpx
from celery import Task

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import async_session_factory
from app.models.video import Video

logger = logging.getLogger(__name__)

ELEVENLABS_BASE = "https://api.elevenlabs.io"
TTS_MODEL = "eleven_turbo_v2_5"


# ── ElevenLabs REST call ───────────────────────────────────────────────────────


def _call_elevenlabs(voice_id: str, text: str) -> tuple[bytes, list[dict]]:
    """POST to ElevenLabs with-timestamps endpoint.

    Returns (audio_bytes, word_timestamps).
    word_timestamps is the list from alignment.words in the response.
    Raises httpx.HTTPStatusError on 4xx/5xx; caller handles 429 separately.
    """
    url = f"{ELEVENLABS_BASE}/v1/text-to-speech/{voice_id}/with-timestamps"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": TTS_MODEL,
        "output_format": "mp3_44100_128",
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    body = response.json()
    # audio_base64 field → decode to bytes
    import base64
    audio_bytes = base64.b64decode(body["audio_base64"])
    word_timestamps: list[dict] = body.get("alignment", {}).get("words", [])
    return audio_bytes, word_timestamps


# ── DB helper ─────────────────────────────────────────────────────────────────


async def _update_video_status(video_id: str, status: str) -> None:
    async with async_session_factory() as session:
        video = await session.get(Video, uuid.UUID(video_id))
        if video is not None:
            video.status = status
        await session.commit()


# ── Celery task ────────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.workers.voice_worker.synthesize_voice",
    queue="script",
    max_retries=3,
    default_retry_delay=60,
)
def synthesize_voice(self: Task, video_id: str, script_json: dict) -> dict:
    """Synthesise narration audio for *video_id* via ElevenLabs.

    Steps:
      1. Concatenate all 5 segment texts.
      2. POST to ElevenLabs with-timestamps endpoint.
      3. Write narration.mp3 + timestamps.json under MEDIA_DIR/{video_id}/.
      4. Advance Video status → 'voiced' (or 'voice_skipped' if no API key).
      5. Enqueue fetch_visuals.
    """
    logger.info(
        "synthesize_voice started task_id=%s video_id=%s",
        self.request.id,
        video_id,
    )

    attempt = self.request.retries
    backoff = 60 * (2**attempt)

    # ── 0. guard: skip gracefully when no API key is configured ───────────────
    if not settings.elevenlabs_api_key:
        logger.warning(
            "synthesize_voice skipped task_id=%s video_id=%s reason=no_api_key",
            self.request.id,
            video_id,
        )
        asyncio.run(_update_video_status(video_id, "voice_skipped"))
        _enqueue_visuals(video_id, script_json)
        return {"status": "voice_skipped", "video_id": video_id}

    voice_id = settings.elevenlabs_voice_id or "21m00Tcm4TlvDq8ikWAM"  # default Rachel

    # ── 1. build narration text ────────────────────────────────────────────────
    segments: list[dict] = script_json.get("segments", [])
    narration_text = " ".join(seg["text"] for seg in segments if seg.get("text"))

    if not narration_text:
        raise ValueError("script_json contains no segment text")

    # ── 2. call ElevenLabs ─────────────────────────────────────────────────────
    try:
        audio_bytes, word_timestamps = _call_elevenlabs(voice_id, narration_text)
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 429:
            # Respect rate-limit: use longer backoff
            logger.warning(
                "synthesize_voice rate-limited attempt=%d video_id=%s, retrying in %ds",
                attempt,
                video_id,
                backoff * 2,
            )
            raise self.retry(exc=exc, countdown=backoff * 2)
        logger.error(
            "synthesize_voice HTTP error attempt=%d video_id=%s status=%d: %s",
            attempt,
            video_id,
            status_code,
            exc,
        )
        raise self.retry(exc=exc, countdown=backoff)
    except httpx.RequestError as exc:
        logger.error(
            "synthesize_voice request error attempt=%d video_id=%s: %s",
            attempt,
            video_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=backoff)

    # ── 3. write files ─────────────────────────────────────────────────────────
    output_dir = Path(settings.media_dir) / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / "narration.mp3"
    timestamps_path = output_dir / "timestamps.json"

    audio_path.write_bytes(audio_bytes)
    timestamps_path.write_text(json.dumps(word_timestamps, indent=2), encoding="utf-8")

    logger.info(
        "synthesize_voice files written audio=%s timestamps=%s",
        audio_path,
        timestamps_path,
    )

    # ── 4. persist status ──────────────────────────────────────────────────────
    try:
        asyncio.run(_update_video_status(video_id, "voiced"))
    except Exception as exc:
        logger.error("synthesize_voice DB update failed attempt=%d: %s", attempt, exc)
        raise self.retry(exc=exc, countdown=backoff)

    # ── 5. enqueue visual fetch ────────────────────────────────────────────────
    _enqueue_visuals(video_id, script_json)

    logger.info(
        "synthesize_voice completed task_id=%s video_id=%s",
        self.request.id,
        video_id,
    )
    return {
        "status": "voiced",
        "video_id": video_id,
        "audio_path": str(audio_path),
        "timestamps_path": str(timestamps_path),
        "word_count": len(word_timestamps),
    }


def _enqueue_visuals(video_id: str, script_json: dict) -> None:
    from app.workers.visual_worker import fetch_visuals

    fetch_visuals.apply_async(kwargs={"video_id": video_id, "script_json": script_json})

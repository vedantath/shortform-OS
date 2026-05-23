"""Script generation worker — Anthropic Claude → ScriptOutput → scripts table."""

import asyncio
import json
import logging
import uuid

import anthropic
from celery import Task
from pydantic import ValidationError

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import async_session_factory
from app.models.script import Script
from app.models.trend_signal import TrendSignal
from app.models.video import Video
from app.schemas.script import ScriptOutput
from app.workers.voice_worker import synthesize_voice

logger = logging.getLogger(__name__)

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# ── hook patterns ──────────────────────────────────────────────────────────────

_HOOK_PATTERNS: dict[str, str] = {
    "ai":              "shocking-prediction",
    "technology":      "contrarian-claim",
    "finance":         "shocking-statistic",
    "gaming":          "bold-claim",
    "health":          "provocative-question",
    "entertainment":   "pattern-interrupt",
    "videos":          "pattern-interrupt",
    "business":        "shocking-statistic",
    "science":         "mind-blowing-fact",
}

_HOOK_INSTRUCTIONS: dict[str, str] = {
    "shocking-prediction": (
        "Open with a bold, specific near-future prediction "
        "(e.g. 'In 6 months X will completely replace Y')."
    ),
    "contrarian-claim": (
        "Open by confidently contradicting a widely-held belief "
        "(e.g. 'Everyone thinks X — they're completely wrong')."
    ),
    "shocking-statistic": (
        "Open with a surprising, specific number that reframes the topic."
    ),
    "bold-claim": (
        "Open with a short, punchy declarative that triggers curiosity "
        "(e.g. 'X is dead. Here's why.')."
    ),
    "provocative-question": (
        "Open with a question that makes the viewer doubt something they assumed "
        "(e.g. 'What if X was actually hurting you?')."
    ),
    "pattern-interrupt": (
        "Open with something jarring and unexpected — a counter-intuitive statement "
        "or stark contrast that forces the viewer to stop scrolling."
    ),
    "mind-blowing-fact": (
        "Open with a little-known fact that recontextualises everything "
        "the viewer thinks they know about the topic."
    ),
}


def _pick_hook_pattern(niche: str) -> str:
    niche_lower = niche.lower()
    for key, pattern in _HOOK_PATTERNS.items():
        if key in niche_lower:
            return pattern
    return "pattern-interrupt"


# ── word-count / timing targets ────────────────────────────────────────────────

# At ~160 words / minute natural narration pace.
SEGMENT_TARGETS: dict[str, dict] = {
    "hook":       {"start": 0,  "end": 2,  "min_words": 4,  "max_words": 10,
                   "purpose": "pattern interrupt / immediate grab"},
    "escalation": {"start": 2,  "end": 10, "min_words": 18, "max_words": 28,
                   "purpose": "raise the stakes"},
    "payoff":     {"start": 10, "end": 25, "min_words": 32, "max_words": 50,
                   "purpose": "deliver on the hook promise"},
    "twist":      {"start": 25, "end": 40, "min_words": 32, "max_words": 50,
                   "purpose": "unexpected re-engagement beat"},
    "cta":        {"start": 40, "end": 60, "min_words": 45, "max_words": 60,
                   "purpose": "follow / like / comment"},
}

SYSTEM_PROMPT = (
    "You are an elite short-form video scriptwriter. Your scripts are punchy, "
    "emotionally gripping, and engineered for maximum retention on YouTube Shorts. "
    "You ALWAYS respond with valid JSON only — no markdown, no prose outside the JSON."
)


def _build_user_prompt(topic: str, niche: str, hook_pattern: str) -> str:
    hook_instruction = _HOOK_INSTRUCTIONS.get(hook_pattern, "Open with a striking statement.")
    seg_lines = "\n".join(
        f"  {name:<12} {t['start']:>2}–{t['end']:>2}s  "
        f"{t['min_words']}–{t['max_words']} words  ({t['purpose']})"
        for name, t in SEGMENT_TARGETS.items()
    )
    return f"""\
Write a 60-second YouTube Shorts script about:

  Topic : {topic}
  Niche : {niche}

Hook pattern — {hook_pattern}
{hook_instruction}

Segment timing and word-count targets (narration at ~160 wpm):
{seg_lines}

Return ONLY a JSON object — no markdown fences, no keys beyond those shown:
{{
  "title":       "<YouTube title, ≤ 100 chars>",
  "description": "<YouTube description, ≤ 500 chars>",
  "tags":        ["<tag>", ...],
  "segments": [
    {{"type":"hook",       "text":"...","start_sec":0, "end_sec":2, "visual_keywords":["..."]}},
    {{"type":"escalation", "text":"...","start_sec":2, "end_sec":10,"visual_keywords":["..."]}},
    {{"type":"payoff",     "text":"...","start_sec":10,"end_sec":25,"visual_keywords":["..."]}},
    {{"type":"twist",      "text":"...","start_sec":25,"end_sec":40,"visual_keywords":["..."]}},
    {{"type":"cta",        "text":"...","start_sec":40,"end_sec":60,"visual_keywords":["..."]}}
  ]
}}"""


# ── LLM calls ─────────────────────────────────────────────────────────────────


def _call_anthropic(topic: str, niche: str, hook_pattern: str) -> ScriptOutput:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(topic, niche, hook_pattern)}],
    )
    data = json.loads(response.content[0].text)
    script = ScriptOutput.model_validate(data)
    script.validate_segment_order()
    return script


def _call_openai_stub(topic: str, niche: str, hook_pattern: str) -> ScriptOutput:  # noqa: ARG001
    raise NotImplementedError("OpenAI fallback not yet configured")


# ── DB helpers (async, called via asyncio.run from the sync Celery task) ──────


async def _load_trend_data(trend_signal_id: str) -> dict | None:
    """Return TrendSignal fields as a plain dict safe to use after the session closes."""
    async with async_session_factory() as session:
        trend = await session.get(TrendSignal, uuid.UUID(trend_signal_id))
        if trend is None:
            return None
        # Read all needed attributes while the session is open.
        return {
            "id":                str(trend.id),
            "topic":             trend.topic,
            "niche":             trend.niche,
            "opportunity_score": trend.opportunity_score,
            "velocity":          trend.velocity,
        }


async def _persist_script_result(
    video_id: str,
    script_json: str,
    model_used: str,
) -> None:
    """Write a Script row and advance the Video status scripting → scripted."""
    async with async_session_factory() as session:
        session.add(
            Script(
                video_id=uuid.UUID(video_id),
                content_json=script_json,
                model_used=model_used,
            )
        )
        video = await session.get(Video, uuid.UUID(video_id))
        if video is not None:
            video.status = "scripted"
        await session.commit()


# ── Celery task ────────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.workers.script_worker.generate_script",
    queue="script",
    max_retries=3,
    default_retry_delay=60,
)
def generate_script(
    self: Task,
    video_id: str,
    trend_signal_id: str | None = None,
    topic: str | None = None,
    niche: str | None = None,
) -> dict:
    """Generate a script for *video_id*, persist it, then enqueue voice synthesis.

    Pipeline:
      1. Pull TrendSignal from DB by trend_signal_id (falls back to topic/niche kwargs).
      2. Build LLM prompt with niche + topic + hook_pattern + per-segment word targets.
      3. Call Claude; validate as ScriptOutput.
      4. Write Script row; advance Video status scripting → scripted.
      5. Enqueue synthesize_voice.
    """
    logger.info(
        "generate_script started task_id=%s video_id=%s trend_signal_id=%s",
        self.request.id,
        video_id,
        trend_signal_id,
    )

    attempt = self.request.retries
    backoff = 60 * (2**attempt)

    # ── 1. load trend ──────────────────────────────────────────────────────────
    if trend_signal_id:
        try:
            trend_data = asyncio.run(_load_trend_data(trend_signal_id))
        except Exception as exc:
            logger.error("DB load failed attempt=%d: %s", attempt, exc)
            raise self.retry(exc=exc, countdown=backoff)

        if trend_data:
            topic = trend_data["topic"]
            niche = trend_data["niche"]

    if not topic or not niche:
        raise ValueError(
            "topic and niche are required; supply them directly or via trend_signal_id"
        )

    hook_pattern = _pick_hook_pattern(niche)
    logger.info(
        "generate_script niche=%r topic=%r hook=%r",
        niche, topic, hook_pattern,
    )

    # ── 2. generate ────────────────────────────────────────────────────────────
    try:
        script = _call_anthropic(topic, niche, hook_pattern)
    except anthropic.APIError as exc:
        logger.warning("Anthropic error attempt=%d: %s", attempt, exc)
        try:
            script = _call_openai_stub(topic, niche, hook_pattern)
        except NotImplementedError:
            raise self.retry(exc=exc, countdown=backoff)
    except (json.JSONDecodeError, ValidationError, AssertionError) as exc:
        logger.error("Script validation failed attempt=%d: %s", attempt, exc)
        raise self.retry(exc=exc, countdown=backoff)

    # ── 3. warn on out-of-range word counts (soft check) ──────────────────────
    for seg in script.segments:
        wc = len(seg.text.split())
        tgt = SEGMENT_TARGETS[seg.type]
        if not (tgt["min_words"] <= wc <= tgt["max_words"]):
            logger.warning(
                "segment %s word_count=%d outside target %d–%d",
                seg.type, wc, tgt["min_words"], tgt["max_words"],
            )

    # ── 4. persist ─────────────────────────────────────────────────────────────
    script_json = json.dumps(script.model_dump())
    try:
        asyncio.run(_persist_script_result(video_id, script_json, ANTHROPIC_MODEL))
    except Exception as exc:
        logger.error("DB persist failed attempt=%d: %s", attempt, exc)
        raise self.retry(exc=exc, countdown=backoff)

    # ── 5. enqueue voice synthesis ─────────────────────────────────────────────
    synthesize_voice.apply_async(
        kwargs={"video_id": video_id, "script_json": script.model_dump()}
    )

    result = {
        "video_id": video_id,
        "trend_signal_id": trend_signal_id,
        "script": script.model_dump(),
        "model_used": ANTHROPIC_MODEL,
        "hook_pattern": hook_pattern,
    }

    logger.info(
        "generate_script completed task_id=%s video_id=%s title=%r",
        self.request.id, video_id, script.title,
    )
    return result

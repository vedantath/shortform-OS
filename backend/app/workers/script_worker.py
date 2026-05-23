"""Script generation worker — calls Anthropic Claude to produce a validated ScriptOutput."""

import json
import logging

import anthropic
from celery import Task
from pydantic import ValidationError

from app.core.celery_app import celery_app
from app.core.config import settings
from app.schemas.script import ScriptOutput

logger = logging.getLogger(__name__)

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are an expert short-form video scriptwriter specializing in viral YouTube Shorts.
You write scripts that are punchy, emotionally engaging, and optimised for maximum retention.
You ALWAYS respond with valid JSON only — no markdown, no prose outside the JSON object."""

USER_PROMPT_TEMPLATE = """Write a 60-second YouTube Shorts script about the following topic:

Topic: {topic}
Niche: {niche}

The script MUST follow this exact structure (5 segments, total ≤ 60 seconds):
  - hook       (0–2 s)   : pattern interrupt, immediate grab
  - escalation (2–10 s)  : raise stakes
  - payoff     (10–25 s) : deliver on the hook promise
  - twist      (25–40 s) : unexpected re-engagement beat
  - cta        (40–60 s) : call to action (follow / like / comment)

Return ONLY a JSON object matching this exact schema (no extra keys):
{{
  "title": "<YouTube title, max 100 chars>",
  "description": "<YouTube description, max 500 chars>",
  "tags": ["<tag1>", "<tag2>", ...],
  "segments": [
    {{
      "type": "hook",
      "text": "<spoken narration>",
      "start_sec": 0,
      "end_sec": 2,
      "visual_keywords": ["<keyword1>", "<keyword2>"]
    }},
    {{
      "type": "escalation",
      "text": "<spoken narration>",
      "start_sec": 2,
      "end_sec": 10,
      "visual_keywords": ["<keyword1>", "<keyword2>"]
    }},
    {{
      "type": "payoff",
      "text": "<spoken narration>",
      "start_sec": 10,
      "end_sec": 25,
      "visual_keywords": ["<keyword1>", "<keyword2>"]
    }},
    {{
      "type": "twist",
      "text": "<spoken narration>",
      "start_sec": 25,
      "end_sec": 40,
      "visual_keywords": ["<keyword1>", "<keyword2>"]
    }},
    {{
      "type": "cta",
      "text": "<spoken narration>",
      "start_sec": 40,
      "end_sec": 60,
      "visual_keywords": ["<keyword1>", "<keyword2>"]
    }}
  ]
}}"""


def _call_anthropic(topic: str, niche: str) -> ScriptOutput:
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": USER_PROMPT_TEMPLATE.format(topic=topic, niche=niche),
            }
        ],
    )
    raw_text = response.content[0].text
    data = json.loads(raw_text)
    script = ScriptOutput.model_validate(data)
    script.validate_segment_order()
    return script


def _call_openai_stub(topic: str, niche: str) -> ScriptOutput:  # noqa: ARG001
    # OpenAI fallback — not wired until OPENAI_API_KEY is available
    raise NotImplementedError("OpenAI fallback not yet configured")


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
    topic: str,
    niche: str,
    trend_signal_id: str | None = None,
) -> dict:
    """Generate a validated script for *video_id* and return the serialised ScriptOutput."""
    logger.info(
        "generate_script started task_id=%s video_id=%s topic=%r niche=%r",
        self.request.id,
        video_id,
        topic,
        niche,
    )

    attempt = self.request.retries
    backoff = 60 * (2**attempt)

    try:
        script = _call_anthropic(topic, niche)
    except anthropic.APIError as exc:
        logger.warning(
            "Anthropic API error on attempt %d, trying OpenAI stub: %s", attempt, exc
        )
        try:
            script = _call_openai_stub(topic, niche)
        except NotImplementedError:
            logger.error(
                "OpenAI fallback not configured; retrying in %ds (attempt %d/3)",
                backoff,
                attempt + 1,
            )
            raise self.retry(exc=exc, countdown=backoff)
    except (json.JSONDecodeError, ValidationError, AssertionError) as exc:
        logger.error(
            "Script validation failed on attempt %d: %s", attempt, exc
        )
        raise self.retry(exc=exc, countdown=backoff)

    result = {
        "video_id": video_id,
        "trend_signal_id": trend_signal_id,
        "script": script.model_dump(),
        "model_used": ANTHROPIC_MODEL,
    }

    logger.info(
        "generate_script completed task_id=%s video_id=%s title=%r",
        self.request.id,
        video_id,
        script.title,
    )
    return result

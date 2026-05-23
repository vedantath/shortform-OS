"""shortform-os pipeline CLI — run via: python -m app.cli <command> [options]"""

import argparse
import asyncio
import json
import sys
import time
import uuid

from app.core.database import async_session_factory
from app.models.trend_signal import TrendSignal
from app.models.video import Video
from app.workers.script_worker import (
    ANTHROPIC_MODEL,
    _call_anthropic,
    _persist_script_result,
    _pick_hook_pattern,
    generate_script,
)
from app.workers.trend_worker import (
    DEFAULT_SUBREDDITS,
    NICHE_KEYWORDS,
    OPPORTUNITY_THRESHOLD,
    _save_and_enqueue,
    _scrape_google_trends,
    _scrape_reddit,
)
from app.workers.voice_worker import synthesize_voice


async def _fetch_trend_and_create_video(
    trend_id_str: str,
) -> tuple[str, str, str, str] | None:
    """Fetch a TrendSignal, create a companion Video row, return (topic, niche, trend_id, video_id).

    Returns None if the trend signal is not found.
    """
    try:
        trend_id = uuid.UUID(trend_id_str)
    except ValueError:
        return None

    async with async_session_factory() as session:
        trend = await session.get(TrendSignal, trend_id)
        if trend is None:
            return None
        video_id = uuid.uuid4()
        session.add(Video(id=video_id, trend_signal_id=trend.id, status="scripting"))
        # Read ORM attributes while the session is still open.
        topic, niche, tid = trend.topic, trend.niche, str(trend.id)
        await session.commit()

    return topic, niche, tid, str(video_id)


# ── synchronous in-process pipeline ───────────────────────────────────────────


def _run_pipeline_sync(niche: str, limit: int, keywords: list[str] | None) -> None:
    """Scrape → score → persist → generate script → enqueue voice, all in-process."""
    effective_keywords = keywords or NICHE_KEYWORDS.get(
        niche.lower(), [f"{niche} trends", f"{niche} viral content"]
    )

    # ── 1. scrape ──────────────────────────────────────────────────────────────
    print(f"[1] Scraping trends — niche={niche!r}")
    t0 = time.perf_counter()
    gt_signals = _scrape_google_trends(niche, effective_keywords)
    reddit_signals = _scrape_reddit(niche, DEFAULT_SUBREDDITS)
    elapsed = time.perf_counter() - t0

    all_signals = gt_signals + reddit_signals
    qualifying = sorted(
        [s for s in all_signals if s["opportunity_score"] >= OPPORTUNITY_THRESHOLD],
        key=lambda s: s["opportunity_score"],
        reverse=True,
    )
    print(
        f"    {elapsed:.1f}s — {len(all_signals)} scraped, "
        f"{len(qualifying)} qualifying (threshold={OPPORTUNITY_THRESHOLD})"
    )

    if not qualifying:
        print("    No qualifying trends found — aborting.")
        return

    top_n = qualifying[:limit]
    if len(qualifying) > limit:
        print(f"    Capped at top {limit} by score (pass --limit to change).")

    # ── 2. save to DB ──────────────────────────────────────────────────────────
    print(f"\n[2] Saving {len(top_n)} trend signal(s) to DB …")
    t0 = time.perf_counter()
    pipeline_jobs, skipped = asyncio.run(_save_and_enqueue(top_n, niche))
    elapsed = time.perf_counter() - t0
    print(
        f"    {elapsed:.2f}s — {len(pipeline_jobs)} saved, "
        f"{skipped} duplicate(s) skipped"
    )

    if not pipeline_jobs:
        print("    All trends were processed recently — aborting.")
        return

    # ── 3+. generate + persist + enqueue voice per job ─────────────────────────
    for idx, job in enumerate(pipeline_jobs, start=1):
        topic = job["topic"]
        video_id = job["video_id"]
        hook_pattern = _pick_hook_pattern(niche)

        print(
            f"\n[script {idx}/{len(pipeline_jobs)}] "
            f"topic={topic!r}  hook={hook_pattern!r}"
        )

        print("    Generating script via Claude …")
        t0 = time.perf_counter()
        try:
            script = _call_anthropic(topic, niche, hook_pattern)
        except Exception as exc:
            print(f"    ERROR: {exc}", file=sys.stderr)
            continue
        elapsed = time.perf_counter() - t0
        print(f"    {elapsed:.1f}s — title={script.title!r}")

        t0 = time.perf_counter()
        asyncio.run(
            _persist_script_result(video_id, json.dumps(script.model_dump()), ANTHROPIC_MODEL)
        )
        elapsed = time.perf_counter() - t0
        print(f"    {elapsed:.2f}s — persisted to DB, status → 'scripted'")

        synthesize_voice.apply_async(
            kwargs={"video_id": video_id, "script_json": script.model_dump()}
        )
        print(f"    Enqueued synthesize_voice  video_id={video_id}")

    print(f"\nDone — {len(pipeline_jobs)} video(s) advanced to 'scripted'.")


# ── sub-command handlers ───────────────────────────────────────────────────────


def cmd_run_pipeline(args: argparse.Namespace) -> None:
    if args.trend_id:
        result = asyncio.run(_fetch_trend_and_create_video(args.trend_id))
        if result is None:
            print(
                f"Error: trend signal '{args.trend_id}' not found or invalid UUID.",
                file=sys.stderr,
            )
            sys.exit(1)

        topic, niche, trend_signal_id, video_id = result
        task = generate_script.apply_async(
            kwargs={
                "video_id": video_id,
                "topic": topic,
                "niche": niche,
                "trend_signal_id": trend_signal_id,
            }
        )
        print(f"Enqueued generate_script")
        print(f"  task_id          = {task.id}")
        print(f"  video_id         = {video_id}")
        print(f"  trend_signal_id  = {trend_signal_id}")
        print(f"  topic            = {topic!r}")
        print(f"  niche            = {niche!r}")
    else:
        keywords = (
            [k.strip() for k in args.keywords.split(",")]
            if args.keywords
            else None
        )
        _run_pipeline_sync(niche=args.niche, limit=args.limit, keywords=keywords)


# ── entry point ────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="shortform-os pipeline CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser(
        "run-pipeline",
        help="Trigger one full pipeline cycle (scrape → score → script → …)",
    )
    p.add_argument(
        "--trend-id",
        metavar="UUID",
        help=(
            "Skip trend scraping — generate a script immediately for this "
            "existing trend signal ID."
        ),
    )
    p.add_argument(
        "--niche",
        default="ai",
        metavar="NAME",
        help="Niche to scrape (default: ai). Ignored when --trend-id is given.",
    )
    p.add_argument(
        "--keywords",
        metavar="KW1,KW2,...",
        help="Comma-separated keyword overrides for Google Trends.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=1,
        metavar="N",
        help="Maximum number of trends to script in one run (default: 1).",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "run-pipeline":
        cmd_run_pipeline(args)


if __name__ == "__main__":
    main()

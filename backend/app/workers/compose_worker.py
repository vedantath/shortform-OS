import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.compose_worker.compose_video",
    queue="render",
    max_retries=3,
    default_retry_delay=60,
)
def compose_video(self, video_id: str, audio_path: str, clips: list[str]) -> dict:
    logger.info(
        "compose_video started task_id=%s video_id=%s", self.request.id, video_id
    )
    # TODO: implement FFmpeg 1080x1920 composition with captions
    logger.info("compose_video completed task_id=%s", self.request.id)
    return {"status": "stub", "video_id": video_id}

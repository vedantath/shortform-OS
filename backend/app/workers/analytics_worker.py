import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.analytics_worker.collect_analytics",
    queue="analytics",
    max_retries=3,
    default_retry_delay=60,
)
def collect_analytics(self, video_id: str, youtube_video_id: str) -> dict:
    logger.info(
        "collect_analytics started task_id=%s video_id=%s yt_id=%s",
        self.request.id,
        video_id,
        youtube_video_id,
    )
    # TODO: implement YouTube Analytics API data pull
    logger.info("collect_analytics completed task_id=%s", self.request.id)
    return {"status": "stub", "video_id": video_id}

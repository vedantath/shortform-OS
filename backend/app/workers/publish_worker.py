import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.publish_worker.publish_video",
    queue="upload",
    max_retries=3,
    default_retry_delay=60,
)
def publish_video(self, video_id: str, video_path: str, metadata: dict) -> dict:
    logger.info(
        "publish_video started task_id=%s video_id=%s", self.request.id, video_id
    )
    # TODO: implement YouTube Data API v3 resumable upload
    logger.info("publish_video completed task_id=%s", self.request.id)
    return {"status": "stub", "video_id": video_id}

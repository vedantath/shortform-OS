import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.visual_worker.fetch_visuals",
    queue="script",
    max_retries=3,
    default_retry_delay=60,
)
def fetch_visuals(self, video_id: str, script_json: dict) -> dict:
    logger.info(
        "fetch_visuals started task_id=%s video_id=%s", self.request.id, video_id
    )
    # TODO: implement Pexels + Pixabay keyword search and clip download
    logger.info("fetch_visuals completed task_id=%s", self.request.id)
    return {"status": "stub", "video_id": video_id}

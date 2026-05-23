import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.voice_worker.synthesize_voice",
    queue="script",
    max_retries=3,
    default_retry_delay=60,
)
def synthesize_voice(self, video_id: str, script_json: dict) -> dict:
    logger.info(
        "synthesize_voice started task_id=%s video_id=%s", self.request.id, video_id
    )
    # TODO: implement ElevenLabs TTS with word timestamps
    logger.info("synthesize_voice completed task_id=%s", self.request.id)
    return {"status": "stub", "video_id": video_id}

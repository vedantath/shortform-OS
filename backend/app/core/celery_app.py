from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "shortform_os",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.trend_worker",
        "app.workers.script_worker",
        "app.workers.voice_worker",
        "app.workers.visual_worker",
        "app.workers.compose_worker",
        "app.workers.publish_worker",
        "app.workers.analytics_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_queues={
        "trend": {"exchange": "trend", "routing_key": "trend"},
        "script": {"exchange": "script", "routing_key": "script"},
        "render": {"exchange": "render", "routing_key": "render"},
        "upload": {"exchange": "upload", "routing_key": "upload"},
        "analytics": {"exchange": "analytics", "routing_key": "analytics"},
    },
    task_default_queue="script",
    task_default_exchange="script",
    task_default_routing_key="script",
)

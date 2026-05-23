import uuid
from datetime import datetime

from pydantic import BaseModel


class VideoRead(BaseModel):
    id: uuid.UUID
    trend_signal_id: uuid.UUID | None
    channel_id: uuid.UUID | None
    status: str
    title: str | None
    description: str | None
    tags: str | None
    youtube_video_id: str | None
    local_path: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoCreate(BaseModel):
    trend_signal_id: uuid.UUID | None = None
    channel_id: uuid.UUID | None = None

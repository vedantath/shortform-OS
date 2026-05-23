import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TrendSignalCreate(BaseModel):
    source: str
    niche: str
    topic: str
    virality_score: float = Field(0.0, ge=0, le=100)
    engagement_score: float = Field(0.0, ge=0, le=100)
    monetization_score: float = Field(0.0, ge=0, le=100)
    saturation_score: float = Field(0.0, ge=0, le=100)
    velocity: float = Field(0.0, ge=0)
    raw_data: str | None = None


class TrendSignalRead(TrendSignalCreate):
    id: uuid.UUID
    opportunity_score: float
    created_at: datetime

    model_config = {"from_attributes": True}

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class TrendSignal(Base):
    __tablename__ = "trend_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    niche: Mapped[str] = mapped_column(String(128), nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    virality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    engagement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monetization_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    saturation_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    opportunity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    velocity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

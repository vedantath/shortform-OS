import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.trend_signal import TrendSignal
from app.schemas.trend import TrendSignalCreate, TrendSignalRead

router = APIRouter(prefix="/trends", tags=["trends"])

SCORE_WEIGHTS = {
    "virality": 0.40,
    "engagement": 0.25,
    "monetization": 0.20,
    "saturation": -0.15,
}


def _compute_opportunity_score(data: TrendSignalCreate) -> float:
    return (
        SCORE_WEIGHTS["virality"] * data.virality_score
        + SCORE_WEIGHTS["engagement"] * data.engagement_score
        + SCORE_WEIGHTS["monetization"] * data.monetization_score
        + SCORE_WEIGHTS["saturation"] * data.saturation_score
    )


@router.get("/", response_model=list[TrendSignalRead])
async def list_trends(session: AsyncSession = Depends(get_session)) -> list[TrendSignalRead]:
    result = await session.execute(
        select(TrendSignal).order_by(TrendSignal.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/", response_model=TrendSignalRead, status_code=201)
async def create_trend(
    body: TrendSignalCreate, session: AsyncSession = Depends(get_session)
) -> TrendSignalRead:
    opportunity_score = _compute_opportunity_score(body)
    signal = TrendSignal(**body.model_dump(), opportunity_score=opportunity_score)
    session.add(signal)
    await session.commit()
    await session.refresh(signal)
    return TrendSignalRead.model_validate(signal)


@router.get("/{trend_id}", response_model=TrendSignalRead)
async def get_trend(
    trend_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> TrendSignalRead:
    signal = await session.get(TrendSignal, trend_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Trend signal not found")
    return TrendSignalRead.model_validate(signal)

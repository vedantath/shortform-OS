import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.video import Video
from app.schemas.video import VideoCreate, VideoRead
from app.workers.script_worker import generate_script

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/", response_model=list[VideoRead])
async def list_videos(session: AsyncSession = Depends(get_session)) -> list[VideoRead]:
    result = await session.execute(select(Video).order_by(Video.created_at.desc()))
    return list(result.scalars().all())


@router.post("/", response_model=VideoRead, status_code=201)
async def create_video(
    body: VideoCreate, session: AsyncSession = Depends(get_session)
) -> VideoRead:
    video = Video(**body.model_dump())
    session.add(video)
    await session.commit()
    await session.refresh(video)
    return VideoRead.model_validate(video)


@router.get("/{video_id}", response_model=VideoRead)
async def get_video(
    video_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> VideoRead:
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return VideoRead.model_validate(video)


@router.post("/{video_id}/generate-script", status_code=202)
async def trigger_script_generation(
    video_id: uuid.UUID,
    topic: str,
    niche: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    video = await session.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    task = generate_script.apply_async(
        kwargs={
            "video_id": str(video_id),
            "topic": topic,
            "niche": niche,
            "trend_signal_id": str(video.trend_signal_id) if video.trend_signal_id else None,
        }
    )
    return {"task_id": task.id, "video_id": str(video_id)}

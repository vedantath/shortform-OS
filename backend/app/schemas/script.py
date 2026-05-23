from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class SegmentType(str, Enum):
    hook = "hook"
    escalation = "escalation"
    payoff = "payoff"
    twist = "twist"
    cta = "cta"


class ScriptSegment(BaseModel):
    type: SegmentType
    text: str = Field(..., min_length=1, description="Spoken narration text")
    start_sec: int = Field(..., ge=0, le=60)
    end_sec: int = Field(..., ge=0, le=60)
    visual_keywords: Annotated[list[str], Field(min_length=1, max_length=5)]

    model_config = {"use_enum_values": True}


class ScriptOutput(BaseModel):
    """Structured JSON output expected from the LLM for a 60-second short."""

    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    tags: Annotated[list[str], Field(min_length=1, max_length=30)]
    segments: Annotated[list[ScriptSegment], Field(min_length=5, max_length=5)]

    def validate_segment_order(self) -> "ScriptOutput":
        expected = [t.value for t in SegmentType]
        actual = [s.type for s in self.segments]
        assert actual == expected, f"Segment order must be {expected}, got {actual}"
        return self

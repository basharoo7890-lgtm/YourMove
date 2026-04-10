from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SessionStartRequest(BaseModel):
    access_key: str = Field(min_length=5, max_length=20)
    doctor_name: Optional[str] = Field(default=None, max_length=120)


class SessionStartResponse(BaseModel):
    session_id: int
    patient_name: str
    sensory_profile: dict
    learning_style: Optional[str] = None
    baseline_duration_seconds: int = 120


class SessionOut(BaseModel):
    id: int
    patient_id: int
    therapist_id: int
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    pre_session_mood: Optional[str] = None
    post_session_mood: Optional[str] = None
    session_notes: Optional[str] = ""
    config: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

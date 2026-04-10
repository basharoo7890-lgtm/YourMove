from typing import Optional

from pydantic import BaseModel, Field, field_validator


class GameEventData(BaseModel):
    event: str = "interaction"
    reaction_time_ms: Optional[float] = Field(default=None, ge=0)
    is_correct: Optional[bool] = None
    round: Optional[int] = Field(default=None, ge=0)
    difficulty_level: Optional[int] = Field(default=None, ge=0)
    is_baseline: bool = False


class GameEventMessage(BaseModel):
    type: str
    activity_type: str = Field(min_length=1, max_length=30)
    timestamp: Optional[float | str] = None
    data: GameEventData

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value != "game_event":
            raise ValueError("type must be 'game_event'")
        return value


class MotionDataPayload(BaseModel):
    trackers: dict
    total_movement_index: float = 0.0
    tracker_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    is_baseline: bool = False


class MotionDataMessage(BaseModel):
    type: str
    timestamp: Optional[float | str] = None
    data: MotionDataPayload

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value != "motion_data":
            raise ValueError("type must be 'motion_data'")
        return value


class HeadGazePayload(BaseModel):
    hmd_rotation: Optional[dict] = None
    hmd_position: Optional[dict] = None
    is_looking_at_target: Optional[bool] = None
    angle_to_target_degrees: float = Field(default=0.0, ge=0, le=180)
    is_baseline: bool = False


class HeadGazeMessage(BaseModel):
    type: str
    timestamp: Optional[float | str] = None
    data: HeadGazePayload

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value != "head_gaze":
            raise ValueError("type must be 'head_gaze'")
        return value


class SessionEventMessage(BaseModel):
    type: str
    event: str
    activity_type: Optional[str] = ""
    timestamp: Optional[float | str] = None
    is_baseline: Optional[bool] = False
    summary: Optional[dict] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value != "session_event":
            raise ValueError("type must be 'session_event'")
        return value


class DoctorCommandMessage(BaseModel):
    type: str
    command: str = Field(min_length=1, max_length=30)
    value: Optional[str] = None
    doctor_id: Optional[int] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value != "doctor_command":
            raise ValueError("type must be 'doctor_command'")
        return value

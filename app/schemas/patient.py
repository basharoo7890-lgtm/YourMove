from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    age: int = Field(ge=1, le=120)
    gender: Optional[str] = Field(default=None, max_length=10)
    diagnosis: Optional[str] = Field(default=None, max_length=50)
    sensory_profile: dict = Field(default_factory=dict)
    notes: Optional[str] = Field(default="", max_length=5000)


class PatientUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    age: Optional[int] = Field(default=None, ge=1, le=120)
    gender: Optional[str] = Field(default=None, max_length=10)
    diagnosis: Optional[str] = Field(default=None, max_length=50)
    sensory_profile: Optional[dict] = None
    notes: Optional[str] = Field(default=None, max_length=5000)


class PatientOut(BaseModel):
    id: int
    full_name: str
    age: int
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    access_key: str
    sensory_profile: Optional[dict] = None
    notes: Optional[str] = ""
    therapist_id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

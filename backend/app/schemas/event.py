import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=500)
    start_time: datetime
    end_time: datetime | None = None
    priority: PriorityLevel = PriorityLevel.AMARILLO


class EventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=500)
    start_time: datetime | None = None
    end_time: datetime | None = None
    priority: PriorityLevel | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    project_id: uuid.UUID | None
    description: str | None
    location: str | None
    start_time: datetime
    end_time: datetime | None
    priority: PriorityLevel
    created_at: datetime
    updated_at: datetime

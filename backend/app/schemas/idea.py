import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel


class IdeaCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    content: str | None = None
    priority: PriorityLevel = PriorityLevel.VERDE


class IdeaUpdate(BaseModel):
    title: str | None = None
    project_id: uuid.UUID | None = None
    content: str | None = None
    priority: PriorityLevel | None = None


class IdeaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    project_id: uuid.UUID | None
    content: str | None
    priority: PriorityLevel
    created_at: datetime
    updated_at: datetime

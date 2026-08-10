import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus = TaskStatus.PENDIENTE
    priority: PriorityLevel = PriorityLevel.VERDE
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    project_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: PriorityLevel | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    project_id: uuid.UUID | None
    description: str | None
    status: TaskStatus
    priority: PriorityLevel
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

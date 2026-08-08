import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PriorityLevel, ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    company_id: uuid.UUID | None = None
    description: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVO
    priority: PriorityLevel = PriorityLevel.VERDE


class ProjectUpdate(BaseModel):
    name: str | None = None
    company_id: uuid.UUID | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    priority: PriorityLevel | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    company_id: uuid.UUID | None
    description: str | None
    status: ProjectStatus
    priority: PriorityLevel
    created_at: datetime
    updated_at: datetime

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntityType, ReminderStatus


class ReminderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    remind_at: datetime
    related_entity_type: EntityType | None = None
    related_entity_id: uuid.UUID | None = None


class ReminderUpdate(BaseModel):
    title: str | None = None
    remind_at: datetime | None = None
    status: ReminderStatus | None = None


class ReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    remind_at: datetime
    status: ReminderStatus
    related_entity_type: EntityType | None
    related_entity_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

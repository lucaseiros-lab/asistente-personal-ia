import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import EntityType


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#6B7280", max_length=20)


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    created_at: datetime


class EntityTagCreate(BaseModel):
    tag_id: uuid.UUID
    entity_type: EntityType
    entity_id: uuid.UUID

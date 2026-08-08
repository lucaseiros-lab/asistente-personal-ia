import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PreferenceCreate(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    value: Any
    learned_automatically: bool = False


class PreferenceUpdate(BaseModel):
    value: Any


class PreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    value: Any
    learned_automatically: bool
    created_at: datetime
    updated_at: datetime

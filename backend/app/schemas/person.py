import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    company_id: uuid.UUID | None = None
    role: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    relationship_context: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)


class PersonUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    company_id: uuid.UUID | None = None
    role: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    relationship_context: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    company_id: uuid.UUID | None
    role: str | None
    email: str | None
    phone: str | None
    relationship_context: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

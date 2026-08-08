import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PersonCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    company_id: uuid.UUID | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    relationship_context: str | None = None
    notes: str | None = None


class PersonUpdate(BaseModel):
    full_name: str | None = None
    company_id: uuid.UUID | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    relationship_context: str | None = None
    notes: str | None = None


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

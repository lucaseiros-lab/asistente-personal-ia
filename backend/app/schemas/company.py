import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    industry: str | None = None
    website: str | None = None
    notes: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    industry: str | None = None
    website: str | None = None
    notes: str | None = None


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str | None
    website: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

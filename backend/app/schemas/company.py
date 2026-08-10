import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    industry: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=5000)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    industry: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=5000)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    industry: str | None
    website: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

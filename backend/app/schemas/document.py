import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentSourceType, EntityType


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    file_url: str = Field(min_length=1, max_length=1000)
    mime_type: str | None = None
    source: DocumentSourceType = DocumentSourceType.UPLOAD
    extracted_text: str | None = None
    related_entity_type: EntityType | None = None
    related_entity_id: uuid.UUID | None = None


class DocumentUpdate(BaseModel):
    title: str | None = None
    extracted_text: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    file_url: str
    mime_type: str | None
    source: DocumentSourceType
    extracted_text: str | None
    related_entity_type: EntityType | None
    related_entity_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.ai.schemas import ActionType
from app.models.enums import EntityType, MessageInputType, MessageRole, PriorityLevel


class ConversationCreate(BaseModel):
    title: str = Field(default="Nueva conversación", max_length=255)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary: str | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    input_type: MessageInputType
    content: str
    audio_url: str | None
    created_at: datetime


class ChatRequest(BaseModel):
    content: str = Field(min_length=1)
    input_type: MessageInputType = MessageInputType.TEXTO


class ExecutedActionRead(BaseModel):
    type: ActionType
    entity_type: EntityType
    entity_id: uuid.UUID
    title: str


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    user_message: MessageRead
    assistant_message: MessageRead
    priority: PriorityLevel
    needs_clarification: bool
    executed_actions: list[ExecutedActionRead]

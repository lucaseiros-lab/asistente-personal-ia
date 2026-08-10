import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import AIEngine, AIEngineError
from app.api.deps import (
    get_action_executor,
    get_ai_engine,
    get_conversational_memory,
    get_current_active_user,
    get_db_session,
    get_memory_context_builder,
)
from app.core.rate_limit import limiter
from app.memory.conversational import ConversationalMemoryService
from app.memory.orchestrator import MemoryContextBuilder
from app.models.conversation import Conversation
from app.models.enums import MessageRole
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationRead,
    ExecutedActionRead,
    MessageRead,
)
from app.services.action_executor import ActionExecutor
from app.services.crud_base import CRUDBase

router = APIRouter(prefix="/conversations", tags=["conversations"])
crud = CRUDBase[Conversation, ConversationCreate, ConversationCreate](Conversation)


async def _get_owned_conversation(
    db: AsyncSession, *, user_id: uuid.UUID, conversation_id: uuid.UUID
) -> Conversation:
    obj = await crud.get(db, user_id=user_id, id=conversation_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return obj


@router.get("", response_model=list[ConversationRead])
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> list[Conversation]:
    return await crud.list(db, user_id=user.id, limit=limit, offset=offset)


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Conversation:
    return await crud.create(db, user_id=user.id, data=payload)


@router.get("/{conversation_id}", response_model=ConversationRead)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Conversation:
    return await _get_owned_conversation(db, user_id=user.id, conversation_id=conversation_id)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    obj = await _get_owned_conversation(db, user_id=user.id, conversation_id=conversation_id)
    await crud.delete(db, obj=obj)


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def list_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> list[Message]:
    await _get_owned_conversation(db, user_id=user.id, conversation_id=conversation_id)
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    conversation_id: uuid.UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
    ai_engine: AIEngine = Depends(get_ai_engine),
    memory_builder: MemoryContextBuilder = Depends(get_memory_context_builder),
    conversational_memory: ConversationalMemoryService = Depends(get_conversational_memory),
    action_executor: ActionExecutor = Depends(get_action_executor),
) -> ChatResponse:
    conversation = await _get_owned_conversation(db, user_id=user.id, conversation_id=conversation_id)

    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        input_type=payload.input_type,
        content=payload.content,
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(user_message)

    summary_context, recent_turns = await conversational_memory.build_conversation_context(
        db, conversation=conversation
    )
    memory_context = await memory_builder.build(db, user_id=user.id, query=payload.content)
    if summary_context:
        memory_context = f"{summary_context}\n\n{memory_context}" if memory_context else summary_context

    try:
        interpretation = await ai_engine.interpret_message(
            user_message=payload.content,
            conversation_history=recent_turns,
            memory_context=memory_context,
        )
    except AIEngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.ASSISTANT,
        content=interpretation.reply,
        extracted_actions=interpretation.model_dump(mode="json"),
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)

    executed = [
        await action_executor.execute(db, user_id=user.id, action=action)
        for action in interpretation.actions
    ]

    await conversational_memory.maybe_compact(db, conversation=conversation)

    return ChatResponse(
        conversation_id=conversation.id,
        user_message=MessageRead.model_validate(user_message),
        assistant_message=MessageRead.model_validate(assistant_message),
        priority=interpretation.priority,
        needs_clarification=interpretation.needs_clarification,
        executed_actions=[
            ExecutedActionRead(
                type=e.type, entity_type=e.entity_type, entity_id=e.entity_id, title=e.title
            )
            for e in executed
        ],
    )

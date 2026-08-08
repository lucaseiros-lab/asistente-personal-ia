from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import AIEngine
from app.ai.transcription import TranscriptionService
from app.core.security import InvalidTokenError, TokenType, decode_token
from app.db.session import get_db
from app.memory.conversational import ConversationalMemoryService
from app.memory.orchestrator import MemoryContextBuilder
from app.models.user import User
from app.services.action_executor import ActionExecutor

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(token, TokenType.ACCESS)
    except InvalidTokenError as exc:
        raise credentials_error from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_error
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    return user


def get_ai_engine() -> AIEngine:
    return AIEngine()


def get_memory_context_builder() -> MemoryContextBuilder:
    return MemoryContextBuilder()


def get_conversational_memory() -> ConversationalMemoryService:
    return ConversationalMemoryService()


def get_action_executor() -> ActionExecutor:
    return ActionExecutor()


def get_transcription_service() -> TranscriptionService:
    return TranscriptionService()

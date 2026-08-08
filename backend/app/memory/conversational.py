"""Memoria conversacional: historial de mensajes + compresión por resumen.

El historial completo vive en `messages` (nunca se pierde). Para no crecer
el contexto del Motor IA sin límite, cuando una conversación supera un
umbral de mensajes se genera un resumen de los más antiguos y se guarda en
`conversations.summary`, que se antepone al contexto en lugar de esos
mensajes.
"""

import uuid

from openai import AsyncOpenAI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import get_openai_client
from app.ai.schemas import ChatTurn
from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message

RECENT_TURNS_LIMIT = 20
SUMMARIZE_THRESHOLD = 30
MESSAGES_TO_KEEP_AFTER_SUMMARY = 20


class ConversationalMemoryService:
    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        self._client = client or get_openai_client()

    async def get_recent_turns(
        self, db: AsyncSession, *, conversation_id: uuid.UUID, limit: int = RECENT_TURNS_LIMIT
    ) -> list[ChatTurn]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        return [ChatTurn(role=m.role.value, content=m.content) for m in messages]

    async def build_conversation_context(
        self, db: AsyncSession, *, conversation: Conversation
    ) -> tuple[str, list[ChatTurn]]:
        turns = await self.get_recent_turns(db, conversation_id=conversation.id)
        summary_context = (
            f"Resumen de la conversación previa a estos mensajes: {conversation.summary}"
            if conversation.summary
            else ""
        )
        return summary_context, turns

    async def maybe_compact(self, db: AsyncSession, *, conversation: Conversation) -> None:
        """Resume los mensajes más antiguos si la conversación creció demasiado."""

        count_result = await db.execute(
            select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id)
        )
        total = count_result.scalar_one()
        if total <= SUMMARIZE_THRESHOLD:
            return

        to_summarize_count = total - MESSAGES_TO_KEEP_AFTER_SUMMARY
        old_messages_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
            .limit(to_summarize_count)
        )
        old_messages = list(old_messages_result.scalars().all())
        if not old_messages:
            return

        transcript = "\n".join(f"{m.role.value}: {m.content}" for m in old_messages)
        prompt = (
            "Resumí de forma breve y concreta, en español, los hechos, decisiones y compromisos "
            "relevantes de esta parte de una conversación entre un usuario y su asistente ejecutivo. "
            "No inventes información que no esté presente.\n\n"
            f"Resumen previo (si existe): {conversation.summary or 'ninguno'}\n\n"
            f"Conversación a resumir:\n{transcript}"
        )
        completion = await self._client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        new_summary = completion.choices[0].message.content or conversation.summary or ""

        conversation.summary = new_summary.strip()
        await db.commit()

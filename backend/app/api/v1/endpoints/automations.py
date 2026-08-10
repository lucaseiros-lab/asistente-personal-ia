import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import settings
from app.core.rate_limit import limiter
from app.memory.semantic import SemanticMemoryService
from app.models.document import Document
from app.models.enums import EntityType
from app.schemas.automation import InboundAutomationEvent, InboundAutomationEventResult
from app.services.auth_service import get_user_by_email

router = APIRouter(prefix="/automations", tags=["automations"])


@router.post("/webhook", response_model=InboundAutomationEventResult, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("30/minute")
async def receive_automation_event(
    request: Request,
    payload: InboundAutomationEvent,
    x_webhook_token: str = Header(default=""),
    db: AsyncSession = Depends(get_db_session),
) -> InboundAutomationEventResult:
    """Punto de entrada único para automatizaciones externas (n8n).

    Cada integración (Gmail, Drive, WhatsApp, Slack, Outlook...) se resuelve
    como un workflow de n8n que llama a este webhook con un payload
    normalizado. El contenido queda registrado como Documento y se indexa en
    memoria semántica, disponible para el Motor IA en la próxima conversación.
    """

    if not settings.N8N_WEBHOOK_TOKEN or not hmac.compare_digest(
        x_webhook_token, settings.N8N_WEBHOOK_TOKEN
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de webhook inválido")

    user = await get_user_by_email(db, payload.user_email)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    document = Document(
        user_id=user.id,
        title=payload.title,
        file_url=f"n8n://{payload.source.value}",
        source=payload.source,
        extracted_text=payload.content,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    semantic_memory = SemanticMemoryService()
    await semantic_memory.index(
        db,
        user_id=user.id,
        source_type=EntityType.DOCUMENTO,
        source_id=document.id,
        content=f"{payload.title}\n{payload.content}",
    )

    return InboundAutomationEventResult(status="recibido", document_id=document.id)

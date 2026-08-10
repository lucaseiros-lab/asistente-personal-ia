import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import DocumentSourceType


class InboundAutomationEvent(BaseModel):
    """Payload normalizado que cualquier workflow de n8n debe enviar.

    Un mismo contrato sirve para Gmail, Drive, WhatsApp, Slack, etc.: cada
    integración concreta se resuelve como un workflow de n8n distinto que
    transforma el evento nativo del proveedor a esta forma común.
    """

    user_email: EmailStr
    source: DocumentSourceType
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=200_000)


class InboundAutomationEventResult(BaseModel):
    status: str
    document_id: uuid.UUID

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class N8nClient:
    """Dispara eventos salientes hacia workflows de n8n.

    n8n es infraestructura opcional: si no está configurado (N8N_BASE_URL
    vacío) las llamadas son un no-op silencioso, para que el resto del
    sistema nunca dependa de que las automatizaciones estén activas.
    """

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self._base_url = (base_url if base_url is not None else settings.N8N_BASE_URL).rstrip("/")
        self._token = token if token is not None else settings.N8N_WEBHOOK_TOKEN

    @property
    def enabled(self) -> bool:
        return bool(self._base_url)

    async def dispatch_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if not self.enabled:
            return

        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self._base_url}/webhook/{event_type}", json=payload, headers=headers
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            # Una automatización caída nunca debe romper la acción principal del usuario.
            logger.error("n8n_dispatch_failed", event_type=event_type, error=str(exc))

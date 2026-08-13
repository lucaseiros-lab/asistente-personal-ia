from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import PriorityLevel


@dataclass(frozen=True, slots=True)
class ChatTurn:
    role: str
    content: str


class ActionType(StrEnum):
    """Tipos de acción que el Motor IA puede proponer a partir de un mensaje."""

    CREAR_TAREA = "crear_tarea"
    COMPLETAR_TAREA = "completar_tarea"
    CREAR_EVENTO = "crear_evento"
    CREAR_RECORDATORIO = "crear_recordatorio"
    CREAR_IDEA = "crear_idea"
    CREAR_GASTO = "crear_gasto"
    CREAR_PERSONA = "crear_persona"
    CREAR_EMPRESA = "crear_empresa"
    CREAR_PROYECTO = "crear_proyecto"


class AssistantAction(BaseModel):
    """Acción estructurada única. Los campos no aplicables al `type` quedan en null.

    Se usan campos nullable (en vez de una unión discriminada) porque es el
    patrón que mejor soportan los Structured Outputs de los modelos de IA:
    todo campo figura siempre en el schema, aunque sea `null` para un `type`
    dado, en vez de variar la forma del objeto según el tipo de acción.
    """

    type: ActionType = Field(description="Tipo de acción detectada")
    title: str = Field(description="Título breve y claro de la acción o entidad")
    description: str | None = Field(
        default=None, description="Detalle adicional relevante, o null si no aplica"
    )
    priority: PriorityLevel | None = Field(
        default=None,
        description="Prioridad semáforo (rojo/amarillo/verde) para tarea, evento, idea o proyecto",
    )
    due_date: str | None = Field(
        default=None,
        description="Fecha/hora ISO 8601 de vencimiento para tarea o recordatorio, o null",
    )
    start_time: str | None = Field(
        default=None, description="Fecha/hora ISO 8601 de inicio de un evento, o null"
    )
    end_time: str | None = Field(
        default=None, description="Fecha/hora ISO 8601 de fin de un evento, o null"
    )
    location: str | None = Field(default=None, description="Ubicación de un evento, o null")
    amount: float | None = Field(default=None, description="Monto numérico de un gasto, o null")
    currency: str | None = Field(
        default=None, description="Código de moneda ISO de 3 letras (ej. ARS, USD), o null"
    )
    category: str | None = Field(default=None, description="Categoría de un gasto, o null")
    related_person_name: str | None = Field(
        default=None, description="Nombre de una persona relacionada, o null"
    )
    related_company_name: str | None = Field(
        default=None, description="Nombre de una empresa relacionada, o null"
    )
    related_project_name: str | None = Field(
        default=None, description="Nombre de un proyecto relacionado, o null"
    )
    target_reference: str | None = Field(
        default=None,
        description=(
            "Para completar_tarea: título aproximado de la tarea existente a la que se refiere "
            "el usuario, o null"
        ),
    )


class AssistantInterpretation(BaseModel):
    """Salida estructurada única del Motor IA para un mensaje del usuario.

    Este es el único contrato por el que la IA puede comunicar intenciones al
    resto del sistema: nunca se parsea texto libre para extraer acciones.
    """

    reply: str = Field(description="Respuesta breve, clara y en español para mostrar al usuario")
    priority: PriorityLevel = Field(
        description="Prioridad semáforo global de esta interacción (rojo/amarillo/verde)"
    )
    actions: list[AssistantAction] = Field(
        description="Acciones estructuradas detectadas en el mensaje. Lista vacía si no corresponde ninguna."
    )
    needs_clarification: bool = Field(
        description="True si el asistente necesita más información antes de poder ejecutar alguna acción"
    )

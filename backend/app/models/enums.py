from enum import StrEnum


class PriorityLevel(StrEnum):
    """Sistema de semáforo de prioridades."""

    ROJO = "rojo"
    AMARILLO = "amarillo"
    VERDE = "verde"


class TaskStatus(StrEnum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADA = "completada"
    CANCELADA = "cancelada"


class ProjectStatus(StrEnum):
    ACTIVO = "activo"
    PAUSADO = "pausado"
    COMPLETADO = "completado"
    ARCHIVADO = "archivado"


class ReminderStatus(StrEnum):
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageInputType(StrEnum):
    TEXTO = "texto"
    AUDIO = "audio"


class DocumentSourceType(StrEnum):
    UPLOAD = "upload"
    GMAIL = "gmail"
    DRIVE = "drive"
    WHATSAPP = "whatsapp"
    OTRO = "otro"


class EntityType(StrEnum):
    """Tipos de entidad referenciables de forma polimórfica (etiquetas, memoria semántica)."""

    PERSONA = "persona"
    EMPRESA = "empresa"
    PROYECTO = "proyecto"
    CONVERSACION = "conversacion"
    MENSAJE = "mensaje"
    TAREA = "tarea"
    EVENTO = "evento"
    RECORDATORIO = "recordatorio"
    IDEA = "idea"
    GASTO = "gasto"
    DOCUMENTO = "documento"

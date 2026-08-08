from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.ai.transcription import TranscriptionError, TranscriptionService
from app.api.deps import get_current_active_user, get_transcription_service
from app.models.user import User
from app.schemas.voice import TranscriptionResponse

router = APIRouter(prefix="/voice", tags=["voice"])

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # límite de la API de transcripción de OpenAI


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
    transcription_service: TranscriptionService = Depends(get_transcription_service),
) -> TranscriptionResponse:
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio vacío")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="El audio supera el tamaño máximo permitido"
        )

    try:
        text = await transcription_service.transcribe(
            audio_bytes,
            filename=file.filename or "audio.webm",
            content_type=file.content_type or "audio/webm",
        )
    except TranscriptionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return TranscriptionResponse(text=text)

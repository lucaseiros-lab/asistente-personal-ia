import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_session
from app.models.reminder import Reminder
from app.models.user import User
from app.schemas.reminder import ReminderCreate, ReminderRead, ReminderUpdate
from app.services.crud_base import CRUDBase

router = APIRouter(prefix="/reminders", tags=["reminders"])
crud = CRUDBase[Reminder, ReminderCreate, ReminderUpdate](Reminder)


@router.get("", response_model=list[ReminderRead])
async def list_reminders(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> list[Reminder]:
    return await crud.list(db, user_id=user.id, limit=limit, offset=offset)


@router.post("", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    payload: ReminderCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Reminder:
    return await crud.create(db, user_id=user.id, data=payload)


@router.get("/{reminder_id}", response_model=ReminderRead)
async def get_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Reminder:
    obj = await crud.get(db, user_id=user.id, id=reminder_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recordatorio no encontrado")
    return obj


@router.patch("/{reminder_id}", response_model=ReminderRead)
async def update_reminder(
    reminder_id: uuid.UUID,
    payload: ReminderUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Reminder:
    obj = await crud.get(db, user_id=user.id, id=reminder_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recordatorio no encontrado")
    return await crud.update(db, obj=obj, data=payload)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    obj = await crud.get(db, user_id=user.id, id=reminder_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recordatorio no encontrado")
    await crud.delete(db, obj=obj)

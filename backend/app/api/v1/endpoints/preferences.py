import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_session
from app.models.preference import Preference
from app.models.user import User
from app.schemas.preference import PreferenceCreate, PreferenceRead

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=list[PreferenceRead])
async def list_preferences(
    db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_active_user)
) -> list[Preference]:
    result = await db.execute(select(Preference).where(Preference.user_id == user.id))
    return list(result.scalars().all())


@router.put("", response_model=PreferenceRead)
async def upsert_preference(
    payload: PreferenceCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Preference:
    result = await db.execute(
        select(Preference).where(Preference.user_id == user.id, Preference.key == payload.key)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        obj = Preference(user_id=user.id, **payload.model_dump())
        db.add(obj)
    else:
        obj.value = payload.value
        obj.learned_automatically = payload.learned_automatically
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preference(
    preference_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    result = await db.execute(
        select(Preference).where(Preference.user_id == user.id, Preference.id == preference_id)
    )
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferencia no encontrada")
    await db.delete(obj)
    await db.commit()

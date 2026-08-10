import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_session
from app.models.person import Person
from app.models.user import User
from app.schemas.person import PersonCreate, PersonRead, PersonUpdate
from app.services.crud_base import CRUDBase

router = APIRouter(prefix="/people", tags=["people"])
crud = CRUDBase[Person, PersonCreate, PersonUpdate](Person)


@router.get("", response_model=list[PersonRead])
async def list_people(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> list[Person]:
    return await crud.list(db, user_id=user.id, limit=limit, offset=offset)


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
async def create_person(
    payload: PersonCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Person:
    return await crud.create(db, user_id=user.id, data=payload)


@router.get("/{person_id}", response_model=PersonRead)
async def get_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Person:
    obj = await crud.get(db, user_id=user.id, id=person_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")
    return obj


@router.patch("/{person_id}", response_model=PersonRead)
async def update_person(
    person_id: uuid.UUID,
    payload: PersonUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Person:
    obj = await crud.get(db, user_id=user.id, id=person_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")
    return await crud.update(db, obj=obj, data=payload)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    obj = await crud.get(db, user_id=user.id, id=person_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")
    await crud.delete(db, obj=obj)

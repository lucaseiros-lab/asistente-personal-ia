import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_session
from app.models.idea import Idea
from app.models.user import User
from app.schemas.idea import IdeaCreate, IdeaRead, IdeaUpdate
from app.services.crud_base import CRUDBase

router = APIRouter(prefix="/ideas", tags=["ideas"])
crud = CRUDBase[Idea, IdeaCreate, IdeaUpdate](Idea)


@router.get("", response_model=list[IdeaRead])
async def list_ideas(
    db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_active_user)
) -> list[Idea]:
    return await crud.list(db, user_id=user.id)


@router.post("", response_model=IdeaRead, status_code=status.HTTP_201_CREATED)
async def create_idea(
    payload: IdeaCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Idea:
    return await crud.create(db, user_id=user.id, data=payload)


@router.get("/{idea_id}", response_model=IdeaRead)
async def get_idea(
    idea_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Idea:
    obj = await crud.get(db, user_id=user.id, id=idea_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea no encontrada")
    return obj


@router.patch("/{idea_id}", response_model=IdeaRead)
async def update_idea(
    idea_id: uuid.UUID,
    payload: IdeaUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Idea:
    obj = await crud.get(db, user_id=user.id, id=idea_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea no encontrada")
    return await crud.update(db, obj=obj, data=payload)


@router.delete("/{idea_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_idea(
    idea_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    obj = await crud.get(db, user_id=user.id, id=idea_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea no encontrada")
    await crud.delete(db, obj=obj)

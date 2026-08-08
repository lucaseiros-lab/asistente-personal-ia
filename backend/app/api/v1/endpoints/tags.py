import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_session
from app.models.tag import EntityTag, Tag
from app.models.user import User
from app.schemas.tag import EntityTagCreate, TagCreate, TagRead

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
async def list_tags(
    db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_active_user)
) -> list[Tag]:
    result = await db.execute(select(Tag).where(Tag.user_id == user.id))
    return list(result.scalars().all())


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Tag:
    existing = await db.execute(
        select(Tag).where(Tag.user_id == user.id, Tag.name == payload.name)
    )
    obj = existing.scalar_one_or_none()
    if obj is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La etiqueta ya existe")
    obj = Tag(user_id=user.id, **payload.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    result = await db.execute(select(Tag).where(Tag.user_id == user.id, Tag.id == tag_id))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etiqueta no encontrada")
    await db.delete(obj)
    await db.commit()


@router.post("/assign", status_code=status.HTTP_204_NO_CONTENT)
async def assign_tag(
    payload: EntityTagCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    tag_result = await db.execute(select(Tag).where(Tag.user_id == user.id, Tag.id == payload.tag_id))
    if tag_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Etiqueta no encontrada")

    existing = await db.execute(
        select(EntityTag).where(
            EntityTag.tag_id == payload.tag_id,
            EntityTag.entity_type == payload.entity_type,
            EntityTag.entity_id == payload.entity_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(EntityTag(**payload.model_dump()))
    await db.commit()


@router.post("/unassign", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_tag(
    payload: EntityTagCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    result = await db.execute(
        select(EntityTag).where(
            EntityTag.tag_id == payload.tag_id,
            EntityTag.entity_type == payload.entity_type,
            EntityTag.entity_id == payload.entity_id,
        )
    )
    obj = result.scalar_one_or_none()
    if obj is not None:
        await db.delete(obj)
        await db.commit()

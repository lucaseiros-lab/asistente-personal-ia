import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db_session
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.crud_base import CRUDBase

router = APIRouter(prefix="/companies", tags=["companies"])
crud = CRUDBase[Company, CompanyCreate, CompanyUpdate](Company)


@router.get("", response_model=list[CompanyRead])
async def list_companies(
    db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_active_user)
) -> list[Company]:
    return await crud.list(db, user_id=user.id)


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Company:
    return await crud.create(db, user_id=user.id, data=payload)


@router.get("/{company_id}", response_model=CompanyRead)
async def get_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Company:
    obj = await crud.get(db, user_id=user.id, id=company_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    return obj


@router.patch("/{company_id}", response_model=CompanyRead)
async def update_company(
    company_id: uuid.UUID,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> Company:
    obj = await crud.get(db, user_id=user.id, id=company_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    return await crud.update(db, obj=obj, data=payload)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_active_user),
) -> None:
    obj = await crud.get(db, user_id=user.id, id=company_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada")
    await crud.delete(db, obj=obj)

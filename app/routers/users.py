from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_current_admin, get_user_or_404
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate, UserAdminUpdate
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_my_profile(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_my_profile(
    user_in: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    for field, value in user_in.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("", response_model=PaginatedResponse[UserOut])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_admin)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    result = await db.execute(select(User).offset(skip).limit(limit))
    return PaginatedResponse(items=result.scalars().all(), total=total, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user: Annotated[User, Depends(get_user_or_404)],
    _: Annotated[User, Depends(get_current_admin)],
):
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def admin_update_user(
    user_in: UserAdminUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_user_or_404)],
    _: Annotated[User, Depends(get_current_admin)],
):
    for field, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user
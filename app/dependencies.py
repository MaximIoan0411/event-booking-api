import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.security import oauth2_scheme, decode_token
from app.models.user import User
from app.models.event import Event
from app.enums import UserRole


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nu s-au putut valida credențialele",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirat",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cont dezactivat")
    return user


def require_role(*allowed_roles: UserRole):
    async def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nu ai permisiunea necesară pentru această acțiune",
            )
        return current_user
    return role_checker


get_current_admin = require_role(UserRole.ADMIN)
get_current_organizer = require_role(UserRole.ORGANIZER, UserRole.ADMIN)


async def get_event_or_404(
    event_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Event:
    result = await db.execute(
        select(Event).options(selectinload(Event.organizer)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eveniment inexistent")
    return event


async def get_event_owner_or_admin(
    event: Annotated[Event, Depends(get_event_or_404)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Event:
    if current_user.role != UserRole.ADMIN and event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nu ai permisiunea să modifici acest eveniment",
        )
    return event
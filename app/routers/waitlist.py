from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_event_owner_or_admin, run_expiration_sweep
from app.models.user import User
from app.models.waitlist import WaitlistEntry
from app.schemas.waitlist import WaitlistOut

router = APIRouter(tags=["waitlist"], dependencies=[Depends(run_expiration_sweep)])


@router.get("/waitlist/me", response_model=list[WaitlistOut])
async def list_my_waitlist_entries(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.user_id == current_user.id))
    return result.scalars().all()


@router.get("/events/{event_id}/waitlist", response_model=list[WaitlistOut])
async def list_event_waitlist(
    db: Annotated[AsyncSession, Depends(get_db)],
    event=Depends(get_event_owner_or_admin),
):
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.event_id == event.id))
    return result.scalars().all()
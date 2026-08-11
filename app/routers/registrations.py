import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_event_owner_or_admin, run_expiration_sweep
from app.models.user import User
from app.models.registration import Registration
from app.schemas.registration import RegistrationCreate, RegistrationOut, RegistrationResult
from app.schemas.waitlist import WaitlistOut
from app.services.registration_service import register_for_event, confirm_registration, cancel_registration

from fastapi import Request
from app.limiter import limiter

router = APIRouter(tags=["registrations"], dependencies=[Depends(run_expiration_sweep)])


async def _get_own_registration(
    registration_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Registration:
    result = await db.execute(select(Registration).where(Registration.id == registration_id))
    registration = result.scalar_one_or_none()
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Înregistrare inexistentă")
    if registration.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Nu ai acces la această înregistrare")
    return registration


@router.post("/registrations", response_model=RegistrationResult, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_registration(
    request: Request,
    body: RegistrationCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    outcome, obj = await register_for_event(db, body.event_id, current_user.id)
    if outcome == "registered":
        return RegistrationResult(
            status="registered",
            message="Te-ai înscris cu succes. Confirmă în fereastra de timp indicată.",
            registration=RegistrationOut.model_validate(obj),
        )
    return RegistrationResult(
        status="waitlisted",
        message="Evenimentul e complet. Ai fost adăugat pe lista de așteptare.",
        waitlist_entry=WaitlistOut.model_validate(obj),
    )


@router.post("/registrations/{registration_id}/confirm", response_model=RegistrationOut)
async def confirm_own_registration(
    db: Annotated[AsyncSession, Depends(get_db)],
    registration: Annotated[Registration, Depends(_get_own_registration)],
):
    return await confirm_registration(db, registration)


@router.post("/registrations/{registration_id}/cancel", response_model=RegistrationOut)
async def cancel_own_registration(
    db: Annotated[AsyncSession, Depends(get_db)],
    registration: Annotated[Registration, Depends(_get_own_registration)],
):
    return await cancel_registration(db, registration)


@router.get("/registrations/me", response_model=list[RegistrationOut])
async def list_my_registrations(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(select(Registration).where(Registration.user_id == current_user.id))
    return result.scalars().all()


@router.get("/events/{event_id}/registrations", response_model=list[RegistrationOut])
async def list_event_registrations(
    db: Annotated[AsyncSession, Depends(get_db)],
    event=Depends(get_event_owner_or_admin),
):
    result = await db.execute(select(Registration).where(Registration.event_id == event.id))
    return result.scalars().all()
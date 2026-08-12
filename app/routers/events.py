from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import (
    get_db, get_current_organizer, get_current_admin,
    get_event_or_404, get_event_owner_or_admin,run_expiration_sweep,

)
from app.models.event import Event
from app.models.registration import Registration
from app.models.user import User
from app.enums import EventStatus, RegistrationStatus
from app.schemas.event import EventCreate, EventUpdate, EventOut, EventApproval
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/events", tags=["events"])


async def _attach_available_spots(db: AsyncSession, event: Event) -> EventOut:
    count_result = await db.execute(
        select(func.count()).select_from(Registration).where(
            Registration.event_id == event.id,
            Registration.status.in_((RegistrationStatus.PENDING_CONFIRMATION, RegistrationStatus.CONFIRMED)),
        )
    )
    occupied = count_result.scalar_one()
    event_out = EventOut.model_validate(event)
    event_out.available_spots = event.capacity - occupied
    return event_out


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_organizer)],
):
    event = Event(**event_in.model_dump(), status=EventStatus.DRAFT)
    event.organizer = current_user
    db.add(event)
    await db.commit()
    await db.refresh(event, attribute_names=["created_at"])  
    return await _attach_available_spots(db, event)


@router.post("/{event_id}/submit", response_model=EventOut)
async def submit_event_for_approval(
    db: Annotated[AsyncSession, Depends(get_db)],
    event: Annotated[Event, Depends(get_event_owner_or_admin)],
):
    if event.status != EventStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doar evenimentele DRAFT pot fi trimise spre aprobare")
    event.status = EventStatus.PENDING_APPROVAL
    await db.commit()
    return await _attach_available_spots(db, event)


@router.get("", response_model=PaginatedResponse[EventOut])
async def list_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(run_expiration_sweep)],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    total = (await db.execute(
        select(func.count()).select_from(Event).where(Event.status == EventStatus.APPROVED)
    )).scalar_one()

    result = await db.execute(
        select(Event)
        .options(selectinload(Event.organizer))
        .where(Event.status == EventStatus.APPROVED)
        .offset(skip).limit(limit)
    )
    events = result.scalars().all()
    items = [await _attach_available_spots(db, e) for e in events]
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/pending", response_model=list[EventOut])
async def list_pending_events(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_admin)],
):
    result = await db.execute(
        select(Event).options(selectinload(Event.organizer)).where(Event.status == EventStatus.PENDING_APPROVAL)
    )
    return [await _attach_available_spots(db, e) for e in result.scalars().all()]


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    db: Annotated[AsyncSession, Depends(get_db)],
    event: Annotated[Event, Depends(get_event_or_404)],
    _: Annotated[None, Depends(run_expiration_sweep)],
):
    return await _attach_available_spots(db, event)


@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_in: EventUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    event: Annotated[Event, Depends(get_event_owner_or_admin)],
):
    if event.status not in (EventStatus.DRAFT, EventStatus.PENDING_APPROVAL):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evenimentul nu mai poate fi editat")
    for field, value in event_in.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    await db.commit()
    return await _attach_available_spots(db, event)


@router.post("/{event_id}/review", response_model=EventOut)
async def review_event(
    review: EventApproval,
    db: Annotated[AsyncSession, Depends(get_db)],
    event: Annotated[Event, Depends(get_event_or_404)],
    _: Annotated[User, Depends(get_current_admin)],
):
    if event.status != EventStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evenimentul nu așteaptă aprobare")
    event.status = EventStatus.APPROVED if review.action == "approve" else EventStatus.REJECTED
    await db.commit()
    return await _attach_available_spots(db, event)


@router.post("/{event_id}/cancel", response_model=EventOut)
async def cancel_event(
    db: Annotated[AsyncSession, Depends(get_db)],
    event: Annotated[Event, Depends(get_event_owner_or_admin)],
):
    event.status = EventStatus.CANCELLED
    await db.commit()
    return await _attach_available_spots(db, event)
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.waitlist import WaitlistEntry
from app.models.registration import Registration
from app.enums import WaitlistStatus, RegistrationStatus, EventStatus
from app.models.event import Event

from app.config import get_settings

settings = get_settings()


async def promote_next_from_waitlist(db: AsyncSession, event_id: uuid.UUID) -> WaitlistEntry | None:
    result = await db.execute(
        select(WaitlistEntry)
        .where(WaitlistEntry.event_id == event_id, WaitlistEntry.status == WaitlistStatus.WAITING)
        .order_by(WaitlistEntry.position.asc())
        .with_for_update()
        .limit(1)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return None

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.WAITLIST_CONFIRMATION_WINDOW_MINUTES
    )
    entry.status = WaitlistStatus.PROMOTED
    entry.promoted_at = datetime.now(timezone.utc)
    entry.expires_at = expires_at

    registration = Registration(
        user_id=entry.user_id,
        event_id=entry.event_id,
        status=RegistrationStatus.PENDING_CONFIRMATION,
        confirmation_expires_at=expires_at,
    )
    db.add(registration)
    await db.commit()
    return entry


async def close_completed_events(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Event).where(Event.status == EventStatus.APPROVED, Event.end_time < now)
    )
    events_to_close = result.scalars().all()

    for event in events_to_close:
        event.status = EventStatus.COMPLETED

        pending_result = await db.execute(
            select(Registration).where(
                Registration.event_id == event.id,
                Registration.status == RegistrationStatus.PENDING_CONFIRMATION,
            )
        )
        for reg in pending_result.scalars().all():
            reg.status = RegistrationStatus.EXPIRED

        waiting_result = await db.execute(
            select(WaitlistEntry).where(
                WaitlistEntry.event_id == event.id,
                WaitlistEntry.status == WaitlistStatus.WAITING,
            )
        )
        for entry in waiting_result.scalars().all():
            entry.status = WaitlistStatus.EXPIRED

    if events_to_close:
        await db.commit()


async def expire_stale_entries(db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Registration).where(
            Registration.status == RegistrationStatus.PENDING_CONFIRMATION,
            Registration.confirmation_expires_at < now,
        )
    )
    freed_event_ids = {reg.event_id for reg in result.scalars().all()}
    for reg in (await db.execute(
        select(Registration).where(
            Registration.status == RegistrationStatus.PENDING_CONFIRMATION,
            Registration.confirmation_expires_at < now,
        )
    )).scalars().all():
        reg.status = RegistrationStatus.EXPIRED

    wl_result = await db.execute(
        select(WaitlistEntry).where(
            WaitlistEntry.status == WaitlistStatus.PROMOTED,
            WaitlistEntry.expires_at < now,
        )
    )
    for entry in wl_result.scalars().all():
        entry.status = WaitlistStatus.EXPIRED
        freed_event_ids.add(entry.event_id)

    await db.commit()

    for event_id in freed_event_ids:
        await promote_next_from_waitlist(db, event_id)
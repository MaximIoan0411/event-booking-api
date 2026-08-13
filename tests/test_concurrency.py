import asyncio

from sqlalchemy import select

from app.models.waitlist import WaitlistEntry
from app.enums import WaitlistStatus
from tests.helpers import create_approved_event



async def test_concurrent_registration_only_one_succeeds(
    concurrent_client, organizer_token, admin_token, attendee_token, attendee2_token
):
    
    event_id = await create_approved_event(concurrent_client, organizer_token, admin_token, capacity=1)

    async def register(token):
        return await concurrent_client.post(
            "/registrations",
            json={"event_id": event_id},
            headers={"Authorization": f"Bearer {token}"},
        )

    resp1, resp2 = await asyncio.gather(
        register(attendee_token),
        register(attendee2_token),
    )

    statuses = sorted([resp1.json()["status"], resp2.json()["status"]])
    assert statuses == ["registered", "waitlisted"]


async def test_concurrent_double_cancel_promotes_only_once(
    concurrent_client, db_session, organizer_token, admin_token,
    attendee_token, attendee2_token, attendee3_token,
):
    event_id = await create_approved_event(concurrent_client, organizer_token, admin_token, capacity=1)

    reg_resp = await concurrent_client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    registration_id = reg_resp.json()["registration"]["id"]
    await concurrent_client.post(
        f"/registrations/{registration_id}/confirm",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )

    await concurrent_client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee2_token}"},
    )
    await concurrent_client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee3_token}"},
    )

    async def cancel():
        return await concurrent_client.post(
            f"/registrations/{registration_id}/cancel",
            headers={"Authorization": f"Bearer {attendee_token}"},
        )

    resp1, resp2 = await asyncio.gather(cancel(), cancel())
    statuses = sorted([resp1.status_code, resp2.status_code])
    assert statuses == [200, 400]

    result = await db_session.execute(
        select(WaitlistEntry).where(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.status == WaitlistStatus.PROMOTED,
        )
    )
    promoted = result.scalars().all()
    assert len(promoted) == 1
from sqlalchemy import select
from app.models.registration import Registration
from app.models.waitlist import WaitlistEntry
from app.enums import WaitlistStatus, RegistrationStatus
from tests.helpers import create_approved_event


async def test_register_with_available_capacity(client, organizer_token, admin_token, attendee_token):
    event_id = await create_approved_event(client, organizer_token, admin_token, capacity=1)
    response = await client.post(
        "/registrations",
        json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "registered"


async def test_register_when_full_joins_waitlist(client, organizer_token, admin_token, attendee_token, attendee2_token):
    event_id = await create_approved_event(client, organizer_token, admin_token, capacity=1)
    await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    response = await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee2_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "waitlisted"
    assert data["waitlist_entry"]["position"] == 1


async def test_double_registration_rejected(client, organizer_token, admin_token, attendee_token):
    event_id = await create_approved_event(client, organizer_token, admin_token, capacity=5)
    await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    response = await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 409


async def test_double_waitlist_rejected(client, organizer_token, admin_token, attendee_token, attendee2_token):
    event_id = await create_approved_event(client, organizer_token, admin_token, capacity=1)
    await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee2_token}"},
    )
    response = await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee2_token}"},
    )
    assert response.status_code == 409


async def test_confirm_registration(client, organizer_token, admin_token, attendee_token):
    event_id = await create_approved_event(client, organizer_token, admin_token, capacity=1)
    reg_resp = await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    registration_id = reg_resp.json()["registration"]["id"]

    response = await client.post(
        f"/registrations/{registration_id}/confirm",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


async def test_cancel_triggers_waitlist_promotion(
    client, db_session, organizer_token, admin_token, attendee_token, attendee2_token
):
    event_id = await create_approved_event(client, organizer_token, admin_token, capacity=1)
    reg_resp = await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    registration_id = reg_resp.json()["registration"]["id"]
    await client.post(
        f"/registrations/{registration_id}/confirm",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee2_token}"},
    )

    cancel_resp = await client.post(
        f"/registrations/{registration_id}/cancel",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert cancel_resp.status_code == 200

    result = await db_session.execute(
        select(WaitlistEntry).where(WaitlistEntry.event_id == event_id)
    )
    waitlist_entry = result.scalar_one()
    assert waitlist_entry.status == WaitlistStatus.PROMOTED

    result = await db_session.execute(
        select(Registration).where(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.PENDING_CONFIRMATION,
        )
    )
    new_registration = result.scalar_one()
    assert new_registration is not None


async def test_confirm_others_registration_forbidden(
    client, organizer_token, admin_token, attendee_token, attendee2_token
):
    event_id = await create_approved_event(client, organizer_token, admin_token, capacity=5)
    reg_resp = await client.post(
        "/registrations", json={"event_id": event_id},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    registration_id = reg_resp.json()["registration"]["id"]

    response = await client.post(
        f"/registrations/{registration_id}/confirm",
        headers={"Authorization": f"Bearer {attendee2_token}"},
    )
    assert response.status_code == 403
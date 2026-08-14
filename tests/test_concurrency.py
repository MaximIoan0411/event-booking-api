import asyncio

from tests.helpers import create_approved_event


async def test_concurrent_registration_only_one_succeeds(
    make_concurrent_client, organizer_token, admin_token, attendee_token, attendee2_token
):
    concurrent_client = await make_concurrent_client()
    try:
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
    finally:
        await concurrent_client.aclose()

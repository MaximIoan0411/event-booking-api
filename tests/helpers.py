from datetime import datetime, timedelta, timezone


async def create_approved_event(client, organizer_token, admin_token, capacity, title="Test Event"):
    start = datetime.now(timezone.utc) + timedelta(days=5)
    end = start + timedelta(hours=2)

    create_resp = await client.post(
        "/events",
        json={
            "title": title,
            "description": "desc",
            "capacity": capacity,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    event_id = create_resp.json()["id"]

    await client.post(f"/events/{event_id}/submit", headers={"Authorization": f"Bearer {organizer_token}"})
    await client.post(
        f"/events/{event_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return event_id
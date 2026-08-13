from datetime import datetime, timedelta, timezone


def _valid_times():
    start = datetime.now(timezone.utc) + timedelta(days=5)
    end = start + timedelta(hours=2)
    return start.isoformat(), end.isoformat()


async def test_create_event_rejects_start_time_too_soon(client, organizer_token):
    start = datetime.now(timezone.utc) + timedelta(hours=12)
    end = start + timedelta(hours=2)
    response = await client.post(
        "/events",
        json={
            "title": "Too Soon Workshop",
            "description": "desc",
            "capacity": 10,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    assert response.status_code == 422


async def test_create_event_rejects_end_before_start(client, organizer_token):
    start, _ = _valid_times()
    end = (datetime.now(timezone.utc) + timedelta(days=5) - timedelta(hours=3)).isoformat()
    response = await client.post(
        "/events",
        json={
            "title": "Inverted Times",
            "description": "desc",
            "capacity": 10,
            "start_time": start,
            "end_time": end,
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    assert response.status_code == 422


async def test_attendee_cannot_create_event(client, attendee_token):
    start, end = _valid_times()
    response = await client.post(
        "/events",
        json={
            "title": "Should Fail",
            "description": "desc",
            "capacity": 10,
            "start_time": start,
            "end_time": end,
        },
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 403


async def test_non_owner_cannot_submit_event(client, organizer_token, attendee_token):
    start, end = _valid_times()
    create_resp = await client.post(
        "/events",
        json={
            "title": "Owned By Organizer",
            "description": "desc",
            "capacity": 10,
            "start_time": start,
            "end_time": end,
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    event_id = create_resp.json()["id"]

    response = await client.post(
        f"/events/{event_id}/submit",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 403


async def test_full_approval_workflow(client, organizer_token, admin_token):
    start, end = _valid_times()
    create_resp = await client.post(
        "/events",
        json={
            "title": "Approved Workshop",
            "description": "desc",
            "capacity": 10,
            "start_time": start,
            "end_time": end,
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    assert create_resp.status_code == 201
    event_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "draft"

    submit_resp = await client.post(
        f"/events/{event_id}/submit",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "pending_approval"

    review_resp = await client.post(
        f"/events/{event_id}/review",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "approved"

    public_list = await client.get("/events")
    assert public_list.status_code == 200
    event_ids = [e["id"] for e in public_list.json()["items"]]
    assert event_id in event_ids


async def test_update_event_ignores_capacity(client, organizer_token):
    start, end = _valid_times()
    create_resp = await client.post(
        "/events",
        json={
            "title": "Original Title",
            "description": "desc",
            "capacity": 5,
            "start_time": start,
            "end_time": end,
        },
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    event_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/events/{event_id}",
        json={"title": "Updated Title", "capacity": 999},
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()
    assert data["title"] == "Updated Title"
    assert data["capacity"] == 5
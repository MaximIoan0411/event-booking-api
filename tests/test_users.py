async def test_get_my_profile(client, attendee_token):
    response = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "attendee_fixture@test.com"
    assert "hashed_password" not in data


async def test_update_profile_ignores_role(client, attendee_token):
    response = await client.patch(
        "/users/me",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 200

    check = await client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert check.json()["role"] == "attendee"


async def test_list_users_forbidden_for_non_admin(client, attendee_token):
    response = await client.get(
        "/users",
        headers={"Authorization": f"Bearer {attendee_token}"},
    )
    assert response.status_code == 403


async def test_list_users_allowed_for_admin(client, admin_token):
    response = await client.get(
        "/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
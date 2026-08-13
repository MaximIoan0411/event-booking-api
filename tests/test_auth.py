from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.security import hash_token


async def test_register_success(client):
    response = await client.post("/auth/register", json={
        "email": "newuser@test.com",
        "password": "parola123",
        "full_name": "New User",
        "role": "attendee",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "attendee"
    assert "hashed_password" not in data


async def test_register_rejects_admin_role(client):
    response = await client.post("/auth/register", json={
        "email": "hacker@test.com",
        "password": "parola123",
        "full_name": "Hacker",
        "role": "admin",
    })
    assert response.status_code == 422


async def test_login_success(client):
    await client.post("/auth/register", json={
        "email": "loginuser@test.com",
        "password": "parola123",
        "full_name": "Login User",
        "role": "attendee",
    })
    response = await client.post("/auth/login", data={
        "username": "loginuser@test.com",
        "password": "parola123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={
        "email": "wrongpass@test.com",
        "password": "parola123",
        "full_name": "Wrong Pass",
        "role": "attendee",
    })
    response = await client.post("/auth/login", data={
        "username": "wrongpass@test.com",
        "password": "parolagresita",
    })
    assert response.status_code == 401


async def test_refresh_rotates_token(client, db_session):
    await client.post("/auth/register", json={
        "email": "refreshuser@test.com",
        "password": "parola123",
        "full_name": "Refresh User",
        "role": "attendee",
    })
    login_resp = await client.post("/auth/login", data={
        "username": "refreshuser@test.com",
        "password": "parola123",
    })
    old_refresh = login_resp.json()["refresh_token"]

    refresh_resp = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.json()["refresh_token"]
    assert new_refresh != old_refresh

    old_hash = hash_token(old_refresh)
    result = await db_session.execute(select(RefreshToken).where(RefreshToken.token_hash == old_hash))
    old_token_row = result.scalar_one()
    assert old_token_row.revoked is True


async def test_refresh_rejects_reused_token(client):
    await client.post("/auth/register", json={
        "email": "reuseuser@test.com",
        "password": "parola123",
        "full_name": "Reuse User",
        "role": "attendee",
    })
    login_resp = await client.post("/auth/login", data={
        "username": "reuseuser@test.com",
        "password": "parola123",
    })
    old_refresh = login_resp.json()["refresh_token"]

    await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    second_attempt = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert second_attempt.status_code == 401


async def test_logout_revokes_token(client):
    await client.post("/auth/register", json={
        "email": "logoutuser@test.com",
        "password": "parola123",
        "full_name": "Logout User",
        "role": "attendee",
    })
    login_resp = await client.post("/auth/login", data={
        "username": "logoutuser@test.com",
        "password": "parola123",
    })
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = await client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    refresh_after_logout = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_after_logout.status_code == 401
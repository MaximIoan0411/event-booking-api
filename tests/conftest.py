import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings
from app.database import Base
from app.main import app as fastapi_app
from app.dependencies import get_db
from app.models.user import User
from app.enums import UserRole

from app.limiter import limiter

import app.models 

settings = get_settings()
TEST_DB_URL = settings.TEST_DATABASE_URL

if not TEST_DB_URL or "test" not in TEST_DB_URL:
    raise RuntimeError(
        "Invalid TEST_DATABASE_URL. Tests aborted to protect the production database."
    )

@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limiter():
    limiter.reset()
    yield


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(test_engine, setup_database):
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(test_engine):
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def attendee_token(client):
    await client.post("/auth/register", json={
        "email": "attendee_fixture@test.com",
        "password": "parola123",
        "full_name": "Test Attendee",
        "role": "attendee",
    })
    resp = await client.post("/auth/login", data={
        "username": "attendee_fixture@test.com",
        "password": "parola123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def organizer_token(client):
    await client.post("/auth/register", json={
        "email": "organizer_fixture@test.com",
        "password": "parola123",
        "full_name": "Test Organizer",
        "role": "organizer",
    })
    resp = await client.post("/auth/login", data={
        "username": "organizer_fixture@test.com",
        "password": "parola123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client, db_session):
    await client.post("/auth/register", json={
        "email": "admin_fixture@test.com",
        "password": "parola123",
        "full_name": "Test Admin",
        "role": "attendee",
    })
    result = await db_session.execute(select(User).where(User.email == "admin_fixture@test.com"))
    user = result.scalar_one()
    user.role = UserRole.ADMIN
    await db_session.commit()

    resp = await client.post("/auth/login", data={
        "username": "admin_fixture@test.com",
        "password": "parola123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def concurrent_client(test_engine):
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def attendee2_token(client):
    await client.post("/auth/register", json={
        "email": "attendee2_fixture@test.com",
        "password": "parola123",
        "full_name": "Test Attendee 2",
        "role": "attendee",
    })
    resp = await client.post("/auth/login", data={
        "username": "attendee2_fixture@test.com",
        "password": "parola123",
    })
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def attendee3_token(client):
    await client.post("/auth/register", json={
        "email": "attendee3_fixture@test.com",
        "password": "parola123",
        "full_name": "Test Attendee 3",
        "role": "attendee",
    })
    resp = await client.post("/auth/login", data={
        "username": "attendee3_fixture@test.com",
        "password": "parola123",
    })
    return resp.json()["access_token"]
"""Fixtures compartidas.

Asume que la base de datos apuntada por DATABASE_URL ya tiene el esquema
aplicado (`alembic upgrade head`) y tiene la extensión `vector` habilitada.
En CI esto lo hace el workflow antes de correr pytest; en local, correr
contra una base de test dedicada, nunca contra la de desarrollo:

    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/asistente_test \
        alembic upgrade head && pytest

Cada test crea su propio usuario con un email único (uuid4), lo que aísla
los datos entre tests sin necesidad de truncar tablas ni gestionar
transacciones anidadas sobre un engine async compartido.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.user import User


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """El limiter usa storage en memoria compartido por proceso: sin este reset,
    el volumen de requests de toda la suite podría disparar límites pensados
    para tráfico real de un solo test."""
    limiter.reset()
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def db_user(db_session: AsyncSession, unique_email: str) -> User:
    user = User(email=unique_email, hashed_password=hash_password("password123"), full_name="Test")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def unique_email() -> str:
    return f"test-{uuid.uuid4()}@example.com"


@pytest.fixture
def auth_headers(client: TestClient, unique_email: str) -> dict[str, str]:
    password = "password123"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password, "full_name": "Usuario de Prueba"},
    )
    assert response.status_code == 201, response.text

    response = client.post("/api/v1/auth/login", json={"email": unique_email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

from fastapi.testclient import TestClient


def test_register_login_me_flow(client: TestClient, unique_email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "password123", "full_name": "Lucas"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == unique_email
    assert "hashed_password" not in body

    response = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "password123"})
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == unique_email


def test_register_duplicate_email_is_rejected(client: TestClient, unique_email: str) -> None:
    payload = {"email": unique_email, "password": "password123", "full_name": "Lucas"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_login_with_wrong_password_is_rejected(client: TestClient, unique_email: str) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "password123", "full_name": "Lucas"},
    )
    response = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "wrong"})
    assert response.status_code == 401


def test_refresh_token_issues_new_pair(client: TestClient, unique_email: str) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "password123", "full_name": "Lucas"},
    )
    login = client.post("/api/v1/auth/login", json={"email": unique_email, "password": "password123"})
    refresh_token = login.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_protected_endpoint_without_token_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

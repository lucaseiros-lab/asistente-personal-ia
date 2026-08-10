from fastapi.testclient import TestClient


def test_task_crud_lifecycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    create = client.post("/api/v1/tasks", json={"title": "Tarea 1"}, headers=auth_headers)
    assert create.status_code == 201
    task = create.json()

    listed = client.get("/api/v1/tasks", headers=auth_headers).json()
    assert any(t["id"] == task["id"] for t in listed)

    update = client.patch(
        f"/api/v1/tasks/{task['id']}", json={"status": "completada"}, headers=auth_headers
    )
    assert update.status_code == 200
    assert update.json()["status"] == "completada"

    delete = client.delete(f"/api/v1/tasks/{task['id']}", headers=auth_headers)
    assert delete.status_code == 204

    # soft-delete: ya no aparece listado
    listed_after = client.get("/api/v1/tasks", headers=auth_headers).json()
    assert not any(t["id"] == task["id"] for t in listed_after)


def test_task_list_pagination_is_exposed(client: TestClient, auth_headers: dict[str, str]) -> None:
    for i in range(5):
        client.post("/api/v1/tasks", json={"title": f"Tarea paginada {i}"}, headers=auth_headers)

    first_page = client.get("/api/v1/tasks?limit=2&offset=0", headers=auth_headers)
    assert first_page.status_code == 200
    assert len(first_page.json()) == 2

    second_page = client.get("/api/v1/tasks?limit=2&offset=2", headers=auth_headers)
    assert len(second_page.json()) == 2

    first_ids = {t["id"] for t in first_page.json()}
    second_ids = {t["id"] for t in second_page.json()}
    assert first_ids.isdisjoint(second_ids)

    # limit fuera de rango es rechazado, no truncado silenciosamente
    assert client.get("/api/v1/tasks?limit=1000", headers=auth_headers).status_code == 422
    assert client.get("/api/v1/tasks?limit=0", headers=auth_headers).status_code == 422
    assert client.get("/api/v1/tasks?offset=-1", headers=auth_headers).status_code == 422


def test_task_not_found_returns_404(client: TestClient, auth_headers: dict[str, str]) -> None:
    import uuid

    response = client.get(f"/api/v1/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_crud_endpoints_are_scoped_per_user(client: TestClient) -> None:
    import uuid

    email_a = f"user-a-{uuid.uuid4()}@example.com"
    email_b = f"user-b-{uuid.uuid4()}@example.com"

    user_a = client.post(
        "/api/v1/auth/register",
        json={"email": email_a, "password": "password123", "full_name": "A"},
    )
    user_b = client.post(
        "/api/v1/auth/register",
        json={"email": email_b, "password": "password123", "full_name": "B"},
    )
    assert user_a.status_code == 201 and user_b.status_code == 201

    token_a = client.post(
        "/api/v1/auth/login", json={"email": email_a, "password": "password123"}
    ).json()["access_token"]
    token_b = client.post(
        "/api/v1/auth/login", json={"email": email_b, "password": "password123"}
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    task = client.post("/api/v1/tasks", json={"title": "Solo de A"}, headers=headers_a).json()

    # el usuario B no puede ver ni tocar la tarea del usuario A
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=headers_b).status_code == 404
    assert client.get("/api/v1/tasks", headers=headers_b).json() == []


def test_preferences_upsert_is_idempotent(client: TestClient, auth_headers: dict[str, str]) -> None:
    first = client.put(
        "/api/v1/preferences", json={"key": "tono", "value": "formal"}, headers=auth_headers
    )
    assert first.status_code == 200
    second = client.put(
        "/api/v1/preferences", json={"key": "tono", "value": "informal"}, headers=auth_headers
    )
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["value"] == "informal"

    all_prefs = client.get("/api/v1/preferences", headers=auth_headers).json()
    assert len(all_prefs) == 1


def test_tags_create_duplicate_and_assign_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    tag = client.post(
        "/api/v1/tags", json={"name": "urgente", "color": "#FF0000"}, headers=auth_headers
    ).json()

    duplicate = client.post("/api/v1/tags", json={"name": "urgente"}, headers=auth_headers)
    assert duplicate.status_code == 409

    project = client.post(
        "/api/v1/projects", json={"name": "Proyecto con etiqueta"}, headers=auth_headers
    ).json()

    assign = client.post(
        "/api/v1/tags/assign",
        json={"tag_id": tag["id"], "entity_type": "proyecto", "entity_id": project["id"]},
        headers=auth_headers,
    )
    assert assign.status_code == 204

    unassign = client.post(
        "/api/v1/tags/unassign",
        json={"tag_id": tag["id"], "entity_type": "proyecto", "entity_id": project["id"]},
        headers=auth_headers,
    )
    assert unassign.status_code == 204

    assert client.delete(f"/api/v1/tags/{tag['id']}", headers=auth_headers).status_code == 204

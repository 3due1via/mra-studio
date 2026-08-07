import uuid


def project_payload(**overrides) -> dict:
    payload = {
        "name": "Officina test",
        "project_type": "Workshop",
        "customer": "MRA",
        "description": "Workspace verticale",
        "status": "draft",
        "progress": 0,
    }
    payload.update(overrides)
    return payload


def create_project(client) -> dict:
    response = client.post("/api/v1/projects", json=project_payload())
    assert response.status_code == 201
    return response.json()


def create_environment(client, project_id: str) -> dict:
    response = client.post(
        f"/api/v1/projects/{project_id}/environments",
        json={
            "name": "Banco lavoro",
            "environment_type": "Officina",
            "area_m2": "24,5",
            "height_m": "2.8",
        },
    )
    assert response.status_code == 201
    return response.json()


def create_object(client, environment_id: str) -> dict:
    response = client.post(
        f"/api/v1/environments/{environment_id}/objects",
        json={
            "category": "Strumento",
            "name": "Multimetro",
            "brand": "MRA",
            "status": "active",
            "metadata_json": {"voltage": 600, "calibrated": True},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_project_crud_and_validation(integration_client):
    project = create_project(integration_client)
    assert integration_client.get("/api/v1/projects").json()[0]["id"] == project["id"]
    assert integration_client.get(f"/api/v1/projects/{project['id']}").status_code == 200

    updated = integration_client.put(
        f"/api/v1/projects/{project['id']}",
        json={"status": "active", "progress": 65},
    )
    assert updated.status_code == 200
    assert updated.json()["progress"] == 65

    assert integration_client.post(
        "/api/v1/projects", json=project_payload(name="  ")
    ).status_code == 422
    assert integration_client.post(
        "/api/v1/projects", json=project_payload(progress=101)
    ).status_code == 422
    assert integration_client.post(
        "/api/v1/projects", json=project_payload(status="unknown")
    ).status_code == 422
    assert integration_client.put(
        f"/api/v1/projects/{project['id']}", json={"name": None}
    ).status_code == 422

    assert integration_client.delete(f"/api/v1/projects/{project['id']}").status_code == 204
    assert integration_client.get(f"/api/v1/projects/{project['id']}").status_code == 404


def test_environment_crud_parent_and_dimensions(integration_client):
    project = create_project(integration_client)
    environment = create_environment(integration_client, project["id"])
    assert environment["area_m2"] == "24.5"
    assert integration_client.get(
        f"/api/v1/projects/{project['id']}/environments"
    ).json()[0]["id"] == environment["id"]
    assert integration_client.get(
        f"/api/v1/environments/{environment['id']}"
    ).status_code == 200

    updated = integration_client.put(
        f"/api/v1/environments/{environment['id']}",
        json={"name": "Zona saldatura", "width_m": "4.2"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Zona saldatura"

    missing_project = uuid.uuid4()
    assert integration_client.post(
        f"/api/v1/projects/{missing_project}/environments",
        json={"name": "Stanza", "environment_type": "Room"},
    ).status_code == 404
    assert integration_client.post(
        f"/api/v1/projects/{project['id']}/environments",
        json={"name": "Stanza", "environment_type": "Room", "area_m2": "invalid"},
    ).status_code == 422
    assert integration_client.post(
        f"/api/v1/projects/{project['id']}/environments",
        json={"name": "Stanza", "environment_type": "Room", "height_m": "0"},
    ).status_code == 422

    assert integration_client.delete(
        f"/api/v1/environments/{environment['id']}"
    ).status_code == 204
    assert integration_client.get(
        f"/api/v1/environments/{environment['id']}"
    ).status_code == 404


def test_object_crud_metadata_and_parent(integration_client):
    project = create_project(integration_client)
    environment = create_environment(integration_client, project["id"])
    item = create_object(integration_client, environment["id"])
    assert item["metadata_json"]["voltage"] == 600
    assert integration_client.get(
        f"/api/v1/environments/{environment['id']}/objects"
    ).json()[0]["id"] == item["id"]
    assert integration_client.get(f"/api/v1/objects/{item['id']}").status_code == 200

    updated = integration_client.put(
        f"/api/v1/objects/{item['id']}",
        json={"status": "maintenance", "serial_number": "SN-001"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "maintenance"

    assert integration_client.post(
        f"/api/v1/environments/{uuid.uuid4()}/objects",
        json={"category": "Tool", "name": "Tester"},
    ).status_code == 404
    assert integration_client.post(
        f"/api/v1/environments/{environment['id']}/objects",
        json={"category": "Tool", "name": "Tester", "metadata_json": ["invalid"]},
    ).status_code == 422
    assert integration_client.post(
        f"/api/v1/environments/{environment['id']}/objects",
        json={"category": "  ", "name": "Tester"},
    ).status_code == 422

    assert integration_client.delete(f"/api/v1/objects/{item['id']}").status_code == 204
    assert integration_client.get(f"/api/v1/objects/{item['id']}").status_code == 404


def test_project_and_environment_deletes_cascade(integration_client):
    project = create_project(integration_client)
    environment = create_environment(integration_client, project["id"])
    item = create_object(integration_client, environment["id"])

    assert integration_client.delete(f"/api/v1/projects/{project['id']}").status_code == 204
    assert integration_client.get(f"/api/v1/environments/{environment['id']}").status_code == 404
    assert integration_client.get(f"/api/v1/objects/{item['id']}").status_code == 404

    second_project = create_project(integration_client)
    second_environment = create_environment(integration_client, second_project["id"])
    second_item = create_object(integration_client, second_environment["id"])
    assert integration_client.delete(
        f"/api/v1/environments/{second_environment['id']}"
    ).status_code == 204
    assert integration_client.get(f"/api/v1/objects/{second_item['id']}").status_code == 404


def test_integration_data_is_isolated(integration_client):
    assert integration_client.get("/api/v1/projects").json() == []
    assert integration_client.get(f"/api/v1/projects/{uuid.uuid4()}").status_code == 404

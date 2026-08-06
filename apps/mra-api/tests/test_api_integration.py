def knowledge_payload(code: str = "KC-INTEGRATION-001") -> dict:
    return {
        "code": code,
        "title": "Scheda integrazione",
        "category": "Test",
        "status": "draft",
        "version": "1.0.0",
        "summary": "Contenuto iniziale",
    }


def project_payload() -> dict:
    return {
        "name": "Officina test",
        "project_type": "Workshop",
        "customer": "MRA",
        "description": "Progetto di integrazione",
        "status": "draft",
        "progress": 0,
    }


def test_knowledge_crud_revisions_and_relations(integration_client):
    first = integration_client.post(
        "/api/v1/knowledge-cards", json=knowledge_payload()
    )
    assert first.status_code == 201
    first_card = first.json()

    duplicate = integration_client.post(
        "/api/v1/knowledge-cards", json=knowledge_payload()
    )
    assert duplicate.status_code == 409

    second = integration_client.post(
        "/api/v1/knowledge-cards",
        json=knowledge_payload("KC-INTEGRATION-002"),
    )
    assert second.status_code == 201
    second_card = second.json()

    updated = integration_client.put(
        f"/api/v1/knowledge-cards/{first_card['id']}",
        json={"title": "Scheda aggiornata"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Scheda aggiornata"

    revisions = integration_client.get(
        f"/api/v1/knowledge-cards/{first_card['id']}/revisions"
    )
    assert revisions.status_code == 200
    assert [item["revision_number"] for item in revisions.json()] == [2, 1]

    restored = integration_client.post(
        f"/api/v1/knowledge-cards/{first_card['id']}/revisions/"
        f"{revisions.json()[-1]['id']}/restore"
    )
    assert restored.status_code == 200
    assert restored.json()["title"] == "Scheda integrazione"

    relation = integration_client.post(
        f"/api/v1/knowledge-cards/{first_card['id']}/relations",
        json={
            "target_id": second_card["id"],
            "relation_type": "related_to",
            "note": "Test relazione",
        },
    )
    assert relation.status_code == 201
    listed = integration_client.get(
        f"/api/v1/knowledge-cards/{first_card['id']}/relations"
    )
    assert listed.status_code == 200
    assert listed.json()[0]["target_id"] == second_card["id"]


def test_projects_environments_and_objects(integration_client):
    created = integration_client.post("/api/v1/projects", json=project_payload())
    assert created.status_code == 201
    project = created.json()

    read = integration_client.get(f"/api/v1/projects/{project['id']}")
    assert read.status_code == 200
    assert read.json()["name"] == "Officina test"

    updated = integration_client.put(
        f"/api/v1/projects/{project['id']}",
        json={"status": "active", "progress": 25},
    )
    assert updated.status_code == 200
    assert updated.json()["progress"] == 25

    environment = integration_client.post(
        f"/api/v1/projects/{project['id']}/environments",
        json={"name": "Banco", "environment_type": "Officina"},
    )
    assert environment.status_code == 201

    item = integration_client.post(
        f"/api/v1/projects/environments/{environment.json()['id']}/objects",
        json={"category": "Utensile", "name": "Multimetro"},
    )
    assert item.status_code == 201
    assert item.json()["name"] == "Multimetro"

    deleted = integration_client.delete(f"/api/v1/projects/{project['id']}")
    assert deleted.status_code == 204
    assert integration_client.get(f"/api/v1/projects/{project['id']}").status_code == 404

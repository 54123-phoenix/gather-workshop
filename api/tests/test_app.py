"""Baseline checks for the features already present in this local demo."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import app as application


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(application, "store", application.MemoryStore())
    with TestClient(application.app) as test_client:
        yield test_client


def register(client, event="e1", email="new@example.test", name="新朋友", **kwargs):
    return client.post(
        f"/api/events/{event}/registrations", json={"name": name, "email": email}, **kwargs
    )


def test_health_identifies_local_demo(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "local-memory-demo"}


def test_seed_events_and_registrations_agree(client):
    events = client.get("/api/events").json()["items"]
    assert [(event["id"], event["activeCount"]) for event in events] == [
        ("e1", 3), ("e2", 2), ("e3", 1)
    ]
    for event in events:
        registrations = client.get(f"/api/events/{event['id']}/registrations").json()["items"]
        assert len(registrations) == event["activeCount"]
        assert all(row["eventId"] == event["id"] for row in registrations)
        assert all(row["email"].endswith("@example.test") for row in registrations)


def test_create_registration_and_update_derived_count(client):
    response = register(client, email=" NEW@example.test ", name=" 新朋友 ")
    assert response.status_code == 201
    registration = response.json()
    assert registration["name"] == "新朋友"
    assert registration["email"] == "new@example.test"
    assert registration["status"] == "active"
    assert registration["createdAt"].endswith("+00:00")
    assert registration in client.get("/api/events/e1/registrations").json()["items"]
    assert client.get("/api/events").json()["items"][0]["activeCount"] == 4


def test_duplicate_email_is_case_insensitive_and_event_scoped(client):
    assert register(client, email=" GUEST1@EXAMPLE.TEST ").status_code == 409
    assert register(client, event="e2", email="guest1@example.test").status_code == 201
    assert client.get("/api/events").json()["items"][0]["activeCount"] == 3


def test_full_event_rejects_new_registration(client):
    assert register(client, event="e3").status_code == 409
    assert len(client.get("/api/events/e3/registrations").json()["items"]) == 1


def test_invalid_input_returns_422_without_writing(client):
    for payload in [{"name": " ", "email": "a@example.test"},
                    {"name": "Guest", "email": "not-an-email"},
                    {"name": "Guest"}]:
        assert client.post("/api/events/e1/registrations", json=payload).status_code == 422
    assert len(client.get("/api/events/e1/registrations").json()["items"]) == 3


def test_unknown_event_returns_404(client):
    assert client.get("/api/events/missing/registrations").status_code == 404
    assert register(client, event="missing").status_code == 404


def test_simulated_write_failure_leaves_state_untouched(client):
    before = client.get("/api/events/e1/registrations").json()
    response = register(client, headers={"X-Demo-Fail": "1", "Origin": "http://localhost:5177"})
    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == "http://localhost:5177"
    assert client.get("/api/events/e1/registrations").json() == before
    assert client.get("/api/events", headers={"X-Demo-Fail": "1"}).status_code == 200


def test_demo_reset_restores_seed(client):
    assert register(client).status_code == 201
    assert client.post("/api/demo/reset").json() == {"ok": True}
    assert client.get("/api/events").json()["items"][0]["activeCount"] == 3
    assert len(client.get("/api/events/e1/registrations").json()["items"]) == 3


def test_concurrent_registrations_cannot_exceed_capacity(client):
    def submit(index):
        return register(client, email=f"concurrent{index}@example.test").status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(submit, range(8)))
    assert statuses.count(201) == 5
    assert statuses.count(409) == 3
    assert client.get("/api/events").json()["items"][0]["activeCount"] == 8

"""Regression and contract checks for the local in-memory demo."""

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


def registrations(client, event="e1"):
    return client.get(f"/api/events/{event}/registrations").json()["items"]


def event(client, event_id="e1"):
    return next(item for item in client.get("/api/events").json()["items"] if item["id"] == event_id)


def cancel(client, registration_id, event_id="e1", **kwargs):
    return client.patch(
        f"/api/events/{event_id}/registrations/{registration_id}",
        json={"status": "cancelled"},
        **kwargs,
    )


def set_capacity(client, capacity, event_id="e1", **kwargs):
    return client.patch(
        f"/api/events/{event_id}", json={"capacity": capacity}, **kwargs
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


def test_full_event_creates_waitlisted_registration_without_changing_active_count(client):
    response = register(client, event="e3")
    assert response.status_code == 201
    assert response.json()["status"] == "waitlisted"
    assert len(registrations(client, "e3")) == 2
    assert event(client, "e3")["activeCount"] == 1


def test_waitlisted_email_cannot_be_submitted_twice(client):
    assert register(client, event="e3", email=" WAIT@example.test ").status_code == 201
    assert register(client, event="e3", email="wait@EXAMPLE.test").status_code == 409
    rows = registrations(client, "e3")
    assert sum(row["email"] == "wait@example.test" for row in rows) == 1


def test_invalid_input_returns_422_without_writing(client):
    for payload in [{"name": " ", "email": "a@example.test"},
                    {"name": "Guest", "email": "not-an-email"},
                    {"name": "Guest"}]:
        assert client.post("/api/events/e1/registrations", json=payload).status_code == 422
    assert len(client.get("/api/events/e1/registrations").json()["items"]) == 3


def test_unknown_event_returns_404(client):
    assert client.get("/api/events/missing/registrations").status_code == 404
    assert register(client, event="missing").status_code == 404
    assert set_capacity(client, 2, "missing").status_code == 404
    assert cancel(client, "r1", "missing").status_code == 404


def test_registration_must_belong_to_event_and_patch_inputs_are_validated(client):
    assert cancel(client, "r1", "e2").status_code == 404
    assert client.patch(
        "/api/events/e1/registrations/r1", json={"status": "active"}
    ).status_code == 422
    assert set_capacity(client, -1).status_code == 422
    assert set_capacity(client, "4").status_code == 422
    assert set_capacity(client, 1.5).status_code == 422
    assert set_capacity(client, True).status_code == 422


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


def test_lost_response_can_follow_a_successful_write(client):
    response = register(client, headers={"X-Demo-Fail": "after"})
    assert response.status_code == 503
    rows = registrations(client)
    assert len(rows) == 4
    assert sum(row["email"] == "new@example.test" for row in rows) == 1
    assert register(client).status_code == 409

    response = register(client, event="e3", headers={"X-Demo-Fail": "after"})
    assert response.status_code == 503
    assert register(client, event="e3").status_code == 409
    queued = [row for row in registrations(client, "e3") if row["email"] == "new@example.test"]
    assert len(queued) == 1
    assert queued[0]["status"] == "waitlisted"


def test_concurrent_registrations_cannot_exceed_capacity(client):
    def submit(index):
        return register(client, email=f"concurrent{index}@example.test").status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(submit, range(8)))
    assert statuses == [201] * 8
    rows = registrations(client)
    assert sum(row["status"] == "active" for row in rows) == 8
    assert sum(row["status"] == "waitlisted" for row in rows) == 3
    assert event(client)["activeCount"] == 8


def test_cancel_active_promotes_waitlisted_in_fifo_order(client):
    first = register(client, event="e3", email="first@example.test").json()
    second = register(client, event="e3", email="second@example.test").json()
    third = register(client, event="e3", email="third@example.test").json()

    response = cancel(client, "r6", "e3")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    rows = {row["id"]: row for row in registrations(client, "e3")}
    assert rows[first["id"]]["status"] == "active"
    assert rows[second["id"]]["status"] == "waitlisted"
    assert rows[third["id"]]["status"] == "waitlisted"

    assert cancel(client, first["id"], "e3").status_code == 200
    rows = {row["id"]: row for row in registrations(client, "e3")}
    assert rows[second["id"]]["status"] == "active"
    assert rows[third["id"]]["status"] == "waitlisted"


def test_cancel_waitlisted_removes_it_from_future_promotion(client):
    withdrawn = register(client, event="e3", email="withdrawn@example.test").json()
    next_in_line = register(client, event="e3", email="next@example.test").json()

    assert cancel(client, withdrawn["id"], "e3").json()["status"] == "cancelled"
    assert cancel(client, "r6", "e3").status_code == 200
    rows = {row["id"]: row for row in registrations(client, "e3")}
    assert rows[withdrawn["id"]]["status"] == "cancelled"
    assert rows[next_in_line["id"]]["status"] == "active"


def test_repeated_cancel_is_a_noop_and_does_not_promote_twice(client):
    first = register(client, event="e3", email="first@example.test").json()
    second = register(client, event="e3", email="second@example.test").json()

    assert cancel(client, "r6", "e3").status_code == 200
    first_snapshot = registrations(client, "e3")
    response = cancel(client, "r6", "e3")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert registrations(client, "e3") == first_snapshot
    rows = {row["id"]: row for row in first_snapshot}
    assert rows[first["id"]]["status"] == "active"
    assert rows[second["id"]]["status"] == "waitlisted"


def test_cancelled_email_can_register_again_as_a_new_record(client):
    assert cancel(client, "r1").status_code == 200
    response = register(client, email=" GUEST1@example.test ", name="再次报名")
    assert response.status_code == 201
    assert response.json()["status"] == "active"
    rows = [row for row in registrations(client) if row["email"] == "guest1@example.test"]
    assert len(rows) == 2
    assert {row["status"] for row in rows} == {"active", "cancelled"}


def test_increasing_capacity_promotes_waitlisted_until_places_are_filled(client):
    first = register(client, event="e3", email="first@example.test").json()
    second = register(client, event="e3", email="second@example.test").json()
    third = register(client, event="e3", email="third@example.test").json()

    response = set_capacity(client, 3, "e3")
    assert response.status_code == 200
    assert response.json()["capacity"] == 3
    assert response.json()["activeCount"] == 3
    rows = {row["id"]: row for row in registrations(client, "e3")}
    assert rows[first["id"]]["status"] == "active"
    assert rows[second["id"]]["status"] == "active"
    assert rows[third["id"]]["status"] == "waitlisted"

    response = set_capacity(client, 4, "e3")
    assert response.status_code == 200
    assert response.json()["activeCount"] == 4
    rows = {row["id"]: row for row in registrations(client, "e3")}
    assert rows[third["id"]]["status"] == "active"


def test_capacity_can_decrease_without_downgrading_active_registrations(client):
    before = registrations(client)
    response = set_capacity(client, 4)
    assert response.status_code == 200
    assert response.json()["capacity"] == 4
    assert response.json()["activeCount"] == 3
    assert registrations(client) == before

    same_capacity_snapshot = registrations(client)
    assert set_capacity(client, 4).status_code == 200
    assert registrations(client) == same_capacity_snapshot


def test_capacity_below_active_count_is_rejected_without_changes(client):
    before_event = event(client)
    before_rows = registrations(client)
    response = set_capacity(client, 2)
    assert response.status_code == 409
    assert event(client) == before_event
    assert registrations(client) == before_rows


def test_capacity_zero_is_allowed_when_no_active_registration_remains(client):
    assert cancel(client, "r6", "e3").status_code == 200
    response = set_capacity(client, 0, "e3")
    assert response.status_code == 200
    assert response.json()["capacity"] == 0
    assert response.json()["activeCount"] == 0


def test_concurrent_same_email_creates_only_one_effective_registration(client):
    def submit(_index):
        return register(client, email="same@example.test").status_code

    with ThreadPoolExecutor(max_workers=8) as executor:
        statuses = list(executor.map(submit, range(8)))
    assert statuses.count(201) == 1
    assert statuses.count(409) == 7
    rows = [row for row in registrations(client) if row["email"] == "same@example.test"]
    assert len(rows) == 1
    assert rows[0]["status"] in {"active", "waitlisted"}


def test_registration_state_is_isolated_between_events(client):
    first = register(client, event="e1", email="shared@example.test").json()
    second = register(client, event="e3", email="shared@example.test").json()
    assert first["status"] == "active"
    assert second["status"] == "waitlisted"

    assert cancel(client, first["id"], "e1").status_code == 200
    e3_row = next(row for row in registrations(client, "e3") if row["id"] == second["id"])
    assert e3_row["status"] == "waitlisted"
    assert event(client, "e3")["activeCount"] == 1


def test_lost_cancel_response_retry_does_not_promote_a_second_person(client):
    first = register(client, event="e3", email="first@example.test").json()
    second = register(client, event="e3", email="second@example.test").json()

    assert cancel(client, "r6", "e3", headers={"X-Demo-Fail": "after"}).status_code == 503
    after_lost_response = registrations(client, "e3")
    rows = {row["id"]: row for row in after_lost_response}
    assert rows[first["id"]]["status"] == "active"
    assert rows[second["id"]]["status"] == "waitlisted"

    assert cancel(client, "r6", "e3").status_code == 200
    assert registrations(client, "e3") == after_lost_response


def test_lost_capacity_response_retry_does_not_promote_a_second_person(client):
    first = register(client, event="e3", email="first@example.test").json()
    second = register(client, event="e3", email="second@example.test").json()

    assert set_capacity(
        client, 2, "e3", headers={"X-Demo-Fail": "after"}
    ).status_code == 503
    after_lost_response = registrations(client, "e3")
    rows = {row["id"]: row for row in after_lost_response}
    assert rows[first["id"]]["status"] == "active"
    assert rows[second["id"]]["status"] == "waitlisted"

    response = set_capacity(client, 2, "e3")
    assert response.status_code == 200
    assert response.json()["activeCount"] == 2
    assert registrations(client, "e3") == after_lost_response


def test_simulated_prewrite_failure_protects_cancel_and_capacity(client):
    before_event = event(client)
    before_rows = registrations(client)
    headers = {"X-Demo-Fail": "1"}
    assert cancel(client, "r1", headers=headers).status_code == 503
    assert set_capacity(client, 4, headers=headers).status_code == 503
    assert event(client) == before_event
    assert registrations(client) == before_rows

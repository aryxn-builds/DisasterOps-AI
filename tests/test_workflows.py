import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from conftest import PASSWORD, PHONE, SECRET, login, provision, register
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from disasterops.main import create_app
from disasterops.models import Account, LocationRequest, LoginSession, SOSReport, now
from disasterops.services.auth import COOKIE, token_digest

API = "/api/v1"


def send_sos(client, **fields):
    return client.post(
        API + "/citizen/sos", json={"request_id": str(uuid4()), **fields}
    )


def sign(body, timestamp=None):
    timestamp = str(int(time.time()) if timestamp is None else timestamp)
    signature = hmac.new(
        SECRET.encode(), body + timestamp.encode(), hashlib.sha256
    ).hexdigest()
    return {"X-Signature": signature, "X-Timestamp": timestamp}


def sms_event(message, event_id="synthetic-1"):
    return json.dumps(
        {
            "id": event_id,
            "event": "sms:received",
            "payload": {"sender": PHONE, "message": message},
        }
    ).encode()


def test_auth_hash_session_roles_and_redacted_errors(client, engine):
    assert send_sos(client).status_code == 401
    assert client.get(API + "/rescue/reports").status_code == 401
    forged = client.post(
        API + "/auth/register",
        json={
            "username": "citizen_1",
            "password": PASSWORD,
            "role": "dispatcher",
        },
    )
    assert forged.status_code == 422
    assert PASSWORD not in forged.text
    register(client)
    denied = client.post(
        API + "/auth/login", json={"username": "citizen_1", "password": "wrong"}
    )
    assert denied.status_code == 401
    session = login(client, "CITIZEN_1")
    cookie = session.headers["set-cookie"]
    assert all(
        attribute in cookie.lower()
        for attribute in ("httponly", "secure", "samesite=strict")
    )
    token = client.cookies.get(COOKIE)
    with Session(engine) as db:
        account = db.scalar(select(Account))
        assert account.password_hash.startswith("$argon2id$")
        assert PASSWORD not in account.password_hash
        assert db.get(LoginSession, token_digest(token)).account_id == account.id
    assert client.get(API + "/rescue/reports").status_code == 403
    assert client.get(API + "/auth/me").headers["cache-control"] == "no-store"
    assert (
        client.post(
            API + "/auth/logout", headers={"Origin": "https://different.test"}
        ).status_code
        == 403
    )
    assert client.post(API + "/auth/logout").status_code == 204
    assert (
        client.get(
            API + "/auth/me", headers={"Cookie": f"{COOKIE}={token}"}
        ).status_code
        == 401
    )


def test_sos_persistence_idempotency_isolation_and_checkin(
    client, app, settings, engine
):
    register(client)
    login(client, "citizen_1")
    request_id = str(uuid4())
    response = send_sos(client, request_id=request_id, latitude=28.6, longitude=77.2)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "acknowledged"
    assert (
        send_sos(client, request_id=request_id, latitude=28.6, longitude=77.2).json()
        == body
    )
    assert send_sos(client, request_id=request_id).status_code == 409
    assert send_sos(client, latitude=91, longitude=77.2).status_code == 422
    assert send_sos(client, longitude=77.2).status_code == 422
    assert send_sos(client, username="someone_else").status_code == 422
    assert send_sos(client).status_code == 201
    check = client.put(API + "/citizen/safety", json={"status": "SAFE"})
    assert check.status_code == 200
    own = API + "/citizen/sos/" + body["report_id"]
    with TestClient(
        create_app(settings, engine), base_url="https://testserver"
    ) as after_restart:
        login(after_restart, "citizen_1")
        data = after_restart.get(own).json()
        assert data["latitude"] == 28.6
        assert "phone" not in data
        assert data["assignment"] is None
        assert after_restart.get(API + "/auth/me").json()["safety_status"] == "SAFE"
    register(client, "other_citizen")
    login(client, "other_citizen")
    assert client.get(own).status_code == 404
    assert client.get(API + "/citizen/sos").json() == []
    assert client.get(API + "/citizens").status_code == 404
    assert client.get(API + "/rescue/live-map").status_code == 404


def test_manual_assignment_requires_dispatcher_and_assigned_responder(client, engine):
    register(client)
    login(client, "citizen_1")
    report = send_sos(client, latitude=28.6, longitude=77.2).json()
    report_id = report["report_id"]
    incident_path = API + "/rescue/incidents"
    assert client.post(incident_path, json={"report_id": report_id}).status_code == 403
    provision(engine, "dispatcher", "dispatcher")
    provision(engine, "responder_a", "responder")
    provision(engine, "responder_b", "responder")
    login(client, "dispatcher")
    row = client.get(API + "/rescue/reports").json()[0]
    assert row["phone"] == PHONE and row["assignment"] is None
    incident = client.post(incident_path, json={"report_id": report_id}).json()["id"]
    assert client.post(incident_path, json={"report_id": report_id}).status_code == 409
    endpoint = f"{incident_path}/{incident}/assignments"
    assert (
        client.post(endpoint, json={"responder_username": "citizen_1"}).status_code
        == 404
    )
    assignment = client.post(
        endpoint, json={"responder_username": "responder_a"}
    ).json()
    assert assignment["status"] == "PENDING"
    assert (
        client.post(endpoint, json={"responder_username": "responder_b"}).status_code
        == 409
    )
    confirm = API + "/rescue/assignments/" + assignment["id"] + "/confirm"
    assert client.post(confirm).status_code == 403
    login(client, "responder_b")
    assert client.get(API + "/rescue/reports").status_code == 403
    assert client.get(API + "/rescue/assignments").json() == []
    assert client.post(confirm).status_code == 404
    login(client, "responder_a")
    assert (
        client.get(API + "/rescue/assignments").json()[0]["report"]["latitude"] == 28.6
    )
    confirmed = client.post(confirm).json()
    assert confirmed["status"] == "CONFIRMED" and confirmed["confirmed_at"]
    assert client.post(confirm).json() == confirmed
    login(client, "citizen_1")
    assert (
        client.get(API + "/citizen/sos/" + report_id).json()["assignment"] == confirmed
    )


def test_sms_rejects_invalid_signatures_and_persists_valid_event(
    client, settings, engine
):
    url = API + "/sms/gateway/webhook"
    raw = sms_event("Help @citizen_1, location unknown")
    assert client.post(url, content=raw).status_code == 401
    assert client.post(url, content=raw + b" ", headers=sign(raw)).status_code == 401
    assert (
        client.post(
            url, content=raw, headers=sign(raw, int(time.time()) - 301)
        ).status_code
        == 401
    )
    malformed = b'{"id":null,"event":"sms:received"}'
    assert (
        client.post(url, content=malformed, headers=sign(malformed)).status_code == 400
    )
    assert client.post(url, content=b"x" * 33000).status_code == 413
    assert client.post(API + "/sms/inbound", content=raw).status_code == 404
    assert client.post(url, content=raw, headers=sign(raw)).json() == {
        "status": "acknowledged"
    }
    with TestClient(
        create_app(settings, engine), base_url="https://testserver"
    ) as restarted:
        assert restarted.post(url, content=raw, headers=sign(raw)).json() == {
            "status": "duplicate_ignored"
        }
    coords = sms_event(
        "DISASTEROPS SOS Lat: 0.000000 Lon: -77.200000 Acc: 10m Bat: 35%", "synthetic-2"
    )
    assert client.post(url, content=coords, headers=sign(coords)).status_code == 200
    with Session(engine) as db:
        reports = db.scalars(
            select(SOSReport).order_by(SOSReport.gateway_event_id)
        ).all()
        assert len(reports) == 2
        assert reports[0].account_id is None and reports[0].latitude is None
        assert reports[0].message == "Help @citizen_1, location unknown"
        assert (
            reports[1].latitude,
            reports[1].longitude,
            reports[1].accuracy_meters,
            reports[1].battery_percentage,
        ) == (0, -77.2, 10, 35)
    settings.android_sms_gateway_webhook_secret = None
    assert client.post(url, content=raw, headers=sign(raw)).status_code == 503


def test_location_consent_is_single_use_expiring_and_owner_scoped(
    client, engine, settings, monkeypatch
):
    from pydantic import SecretStr

    from disasterops.routers import location

    register(client)
    login(client, "citizen_1")
    report = send_sos(client).json()
    url = API + "/locate/request"
    assert client.post(url, json=report).status_code == 403
    provision(engine, "operator_a", "dispatcher")
    provision(engine, "operator_b", "dispatcher")
    login(client, "operator_a")
    request = {"report_id": report["report_id"]}
    assert client.post(url, json=request).status_code == 503
    settings.android_sms_gateway_url = "https://gateway.invalid"
    settings.android_sms_gateway_user = "synthetic"
    settings.android_sms_gateway_password = SecretStr("synthetic")
    tokens = []

    def fake_send(config, phone, token):
        assert phone == PHONE
        tokens.append(token)
        return True

    monkeypatch.setattr(location, "send_location_request", fake_send)
    requested = client.post(url, json=request).json()
    assert requested["status"] == "accepted_by_gateway"
    status_url = API + "/locate/status/" + requested["request_id"]
    assert client.get(status_url).json() == {"status": "PENDING"}
    assert (
        client.get(API + "/rescue/reports").json()[0]["location_request_id"]
        == requested["request_id"]
    )
    login(client, "operator_b")
    assert client.get(status_url).status_code == 404
    assert client.get(API + "/rescue/reports").json()[0]["location_request_id"] is None
    client.post(API + "/auth/logout")
    assert client.get(status_url).status_code == 401
    coordinates = {"token": tokens[0], "latitude": 28.6, "longitude": 77.2}
    assert client.post(API + "/locate/submit", json=coordinates).json() == {
        "status": "received"
    }
    assert client.post(API + "/locate/submit", json=coordinates).status_code == 404
    login(client, "operator_a")
    assert client.get(status_url).json()["longitude"] == 77.2
    second = client.post(url, json=request).json()
    with Session(engine) as db:
        entry = db.get(LocationRequest, second["request_id"])
        entry.expires_at = now() - timedelta(minutes=1)
        db.commit()
    assert (
        client.post(
            API + "/locate/submit", json=coordinates | {"token": tokens[1]}
        ).status_code
        == 404
    )


def test_postgres_concurrent_webhook_deliveries(client, engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("Requires TEST_DATABASE_URL")
    url = API + "/sms/gateway/webhook"
    raw = sms_event("synthetic message")

    def deliver(_):
        return client.post(url, content=raw, headers=sign(raw)).json()["status"]

    with ThreadPoolExecutor(max_workers=4) as workers:
        statuses = list(workers.map(deliver, range(4)))
    assert statuses.count("acknowledged") == 1
    assert statuses.count("duplicate_ignored") == 3


def test_failed_storage_does_not_acknowledge(client, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    from disasterops.routers import citizen

    register(client)
    login(client, "citizen_1")

    def unavailable(*_args):
        raise SQLAlchemyError("private diagnostic")

    monkeypatch.setattr(citizen, "record_sos", unavailable)
    response = send_sos(client)
    assert response.status_code == 503
    assert response.json() == {"detail": "Storage temporarily unavailable"}
    assert client.get(API + "/citizen/sos").json() == []

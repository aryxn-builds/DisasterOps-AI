import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateSchema, DropSchema

from disasterops.config import Settings
from disasterops.main import create_app
from disasterops.models import Account, Base
from disasterops.services.auth import password_hasher

PASSWORD = "synthetic secure test passphrase"
PHONE = "+12025550101"
SECRET = "synthetic-tests-only-gateway-signing-key"


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        database_url=None,
        server_public_url="https://testserver",
        android_sms_gateway_webhook_secret=SECRET,
    )


@pytest.fixture
def engine(monkeypatch):
    postgres = os.environ.get("TEST_DATABASE_URL")
    if not postgres:
        local = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(local)
        try:
            yield local
        finally:
            local.dispose()
        return

    from alembic import command
    from alembic.config import Config

    monkeypatch.setenv("DATABASE_URL", postgres)
    url = Settings().postgres_url()
    schema = "phase0_test_" + uuid4().hex
    admin = create_engine(url, hide_parameters=True)
    local = create_engine(url, hide_parameters=True)

    @event.listens_for(local, "connect")
    def set_search_path(connection, _):
        cursor = connection.cursor()
        cursor.execute(f'SET search_path TO "{schema}"')
        cursor.close()
        connection.commit()

    with admin.begin() as conn:
        conn.execute(CreateSchema(schema))
    try:
        with local.connect() as conn:
            config = Config("alembic.ini")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            command.check(config)
        yield local
    finally:
        local.dispose()
        with admin.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def app(settings, engine):
    return create_app(settings, engine)


@pytest.fixture
def client(app):
    with TestClient(app, base_url="https://testserver") as client:
        yield client


def login(client, username):
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 204, response.text
    return response


def register(client, username="citizen_1"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": PASSWORD,
            "phone": PHONE,
        },
    )
    assert response.status_code == 201, response.text


def provision(engine, username, role):
    with Session(engine) as db:
        db.add(
            Account(
                username=username,
                role=role,
                password_hash=password_hasher.hash(PASSWORD),
            )
        )
        db.commit()

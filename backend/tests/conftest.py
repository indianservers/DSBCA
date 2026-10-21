import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

os.environ["APP_ENV"] = "test"
os.environ["DATA_ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
os.environ["AI_VECTOR_BACKEND"] = "exact"
os.environ["JWT_SECRET_KEY"] = "only-for-isolated-tests-32-characters-long"

from app.models import Base
from app.main import app
from app.core.database import db_session


@pytest.fixture
def client():
    pg = os.environ.get("TEST_DATABASE_URL")
    if pg and "dsbca_test" not in pg:
        raise RuntimeError(
            "TEST_DATABASE_URL must name an isolated dsbca_test database"
        )
    engine = (
        create_engine(pg)
        if pg
        else create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    )
    if not pg:

        @event.listens_for(engine, "connect")
        def foreign_keys(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )
            conn.execute(text("INSERT INTO alembic_version VALUES ('0004')"))
    else:
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())

    def override():
        with Session(engine, expire_on_commit=False) as db:
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    app.dependency_overrides[db_session] = override
    with TestClient(app) as c:
        c.engine = engine
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def account(client, email="test@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": email, "password": "Strong-password-123!"},
    )
    assert response.status_code == 201, response.text
    token = response.json()
    return {"Authorization": "Bearer " + token["access_token"]}, token

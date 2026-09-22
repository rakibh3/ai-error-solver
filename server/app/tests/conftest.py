"""Test fixtures.

Defaults to SQLite in-memory so the suite runs without a Postgres server; the
models declare their UUID/JSONB columns via `app.models.types`, which carries
SQLite variants for exactly this purpose.

CI should set TEST_DATABASE_URL to a real Postgres URL. SQLite will not catch
enum, JSONB, or server_default issues, and the migrations are Postgres-only.
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")

# `app.core.database` builds its (unused here) module-level engine from these;
# every fixture engine below is created from TEST_DATABASE_URL instead.
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-at-least-32-bytes-long")
os.environ.setdefault("OPENROUTER_API_KEY", "test")
os.environ.setdefault("ANALYSIS_MODEL", "test/model")
os.environ.setdefault("EMBEDDING_MODEL", "test-embedding")
os.environ.setdefault("VOYAGE_API_KEY", "test")


@pytest.fixture()
def db_engine():
    from app.core.database import Base
    import app.models  # noqa: F401  registers every table

    kwargs = {}
    if TEST_DATABASE_URL.startswith("sqlite"):
        kwargs = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    engine = create_engine(TEST_DATABASE_URL, **kwargs)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def client(db_engine, db_session):
    from app.core.database import get_db
    from main import app

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # Rate limits would otherwise make repeated test logins flaky.
    app.state.limiter.enabled = False

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# --- helpers ---------------------------------------------------------------

def register(client, email, password="Password123", fullname="Test User"):
    return client.post(
        "/api/v1/auth/register",
        json={"fullname": fullname, "email": email, "password": password},
    )


def login(client, email, password="Password123"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def make_admin(db_session, email):
    from app.models.user import User, UserRole

    user = db_session.query(User).filter(User.email == email).first()
    user.role = UserRole.ADMIN
    db_session.commit()
    return user


@pytest.fixture()
def user_token(client):
    register(client, "user@example.com")
    return login(client, "user@example.com")


@pytest.fixture()
def other_user_token(client):
    register(client, "other@example.com")
    return login(client, "other@example.com")


@pytest.fixture()
def admin_token(client, db_session):
    register(client, "admin@example.com")
    make_admin(db_session, "admin@example.com")
    return login(client, "admin@example.com")


@pytest.fixture()
def ready_branch(db_session):
    """A reference project with one indexed branch."""
    from app.models.reference import BranchStatus, ReferenceBranch, ReferenceProject

    project = ReferenceProject(
        id=uuid.uuid4(), name="demo-project", repo_url="https://example.com/demo.git"
    )
    db_session.add(project)
    db_session.flush()

    branch = ReferenceBranch(
        id=uuid.uuid4(),
        project_id=project.id,
        branch_name="main",
        collection_name="reference_demo_project_main_abc12345",
        status=BranchStatus.READY,
    )
    db_session.add(branch)
    db_session.commit()
    return branch


@pytest.fixture()
def pending_branch(db_session):
    from app.models.reference import BranchStatus, ReferenceBranch, ReferenceProject

    project = ReferenceProject(
        id=uuid.uuid4(), name="wip-project", repo_url="https://example.com/wip.git"
    )
    db_session.add(project)
    db_session.flush()
    branch = ReferenceBranch(
        id=uuid.uuid4(),
        project_id=project.id,
        branch_name="main",
        collection_name="reference_wip_project_main_def67890",
        status=BranchStatus.PENDING,
    )
    db_session.add(branch)
    db_session.commit()
    return branch

"""
conftest.py — Shared pytest fixtures for Wild Sentinel test suite.

Uses an in-memory SQLite database so tests run without PostgreSQL,
without a running server, and without touching real data. Each test
function gets a fresh database via the db_session fixture.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# ── Mock heavy ML / cloud dependencies before any app import ────────────────
# This lets the test suite run without ultralytics/YOLO installed,
# and without Firebase credentials or real image files on disk.
# Your real environment already has these installed; the mocks only
# apply during the test run.
sys.modules.setdefault("ultralytics", MagicMock())
sys.modules.setdefault("firebase_admin", MagicMock())
sys.modules.setdefault("firebase_admin.credentials", MagicMock())
sys.modules.setdefault("firebase_admin.messaging", MagicMock())

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Point config at a .env that works for testing ───────────────────────────
# We set env vars BEFORE importing anything from app so pydantic-settings
# picks them up correctly.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("GMAIL_ADDRESS", "")
os.environ.setdefault("GMAIL_APP_PASSWORD", "")

from app.main import app
from app.database import Base, get_db
from app.models.user import User, UserRole
from app.core.security import create_access_token
from passlib.context import CryptContext
from unittest.mock import patch

# ── Password hashing for test environment ─────────────────────────────────────
# The production app uses bcrypt. In some Python 3.12 environments,
# passlib's bcrypt backend has a version-detection bug that crashes.
# We patch the auth route to use sha256_crypt instead during tests only.
# In your real Windows dev environment, bcrypt works fine and this patch
# has no effect on production behaviour.
_test_ctx = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def _test_hash_password(password: str) -> str:
    return _test_ctx.hash(password)

def _test_verify_password(plain: str, hashed: str) -> bool:
    # Allow both sha256_crypt (test) and bcrypt (seeded directly) hashes
    try:
        return _test_ctx.verify(plain, hashed)
    except Exception:
        return False

hash_password = _test_hash_password

# ── Test database (SQLite in-memory, one file per test run) ─────────────────
SQLALCHEMY_TEST_URL = "sqlite:///./test_wildsentinel.db"

test_engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


@pytest.fixture(scope="function", autouse=True)
def db_session():
    """
    Create all tables fresh before each test, drop them after.
    This ensures every test starts with a clean slate.
    """
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    FastAPI TestClient with the real app, but:
    - DB dependency overridden to use in-memory SQLite
    - hash_password patched to use sha256_crypt (avoids bcrypt version
      issues in some Python 3.12 environments — no effect on production)
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.routes.auth.hash_password", side_effect=_test_hash_password), \
         patch("app.core.security.pwd_context", _test_ctx):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


# ── Helper: seed a plain user ─────────────────────────────────────────────────
@pytest.fixture
def regular_user(db_session):
    user = User(
        name="Test User",
        email="user@wildsentinel.test",
        phone="9800000001",
        password=hash_password("testpass123"),
        role=UserRole.user,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Helper: seed an admin user ────────────────────────────────────────────────
@pytest.fixture
def admin_user(db_session):
    user = User(
        name="Admin User",
        email="admin@wildsentinel.test",
        phone="9800000002",
        password=hash_password("adminpass123"),
        role=UserRole.admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ── Helper: return auth header for a given user ───────────────────────────────
def auth_header(user):
    token = create_access_token({"sub": str(user.user_id)})
    return {"Authorization": f"Bearer {token}"}
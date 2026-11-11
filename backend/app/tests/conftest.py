"""
Pytest configuration for AgentShield tests.

Ensures all tests run against an isolated temporary database in /tmp and NEVER
point to, write to, or mutate the user's real project database (agentshield.db).
Guarantees test isolation even if agentshield.db is mounted or marked read-only.
"""
import atexit
import os
import shutil
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Locate the real project database
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REAL_DB_PATH = os.path.join(_BACKEND_DIR, "agentshield.db")

# 2. Immediately create an isolated temporary SQLite database file
_temp_fd, TEST_DB_PATH = tempfile.mkstemp(prefix="test_agentshield_", suffix=".db")
os.close(_temp_fd)

# Copy state from real database if present (read-only read)
if os.path.exists(REAL_DB_PATH):
    shutil.copyfile(REAL_DB_PATH, TEST_DB_PATH)

# Ensure the temp database copy is readable & writable for tests
os.chmod(TEST_DB_PATH, 0o600)

TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

# 3. Override DATABASE_URL in environment BEFORE app.config or app.database is imported!
os.environ["DATABASE_URL"] = TEST_DB_URL

# 4. Now import config, database, models, and FastAPI app
from app.config import settings
settings.DATABASE_URL = TEST_DB_URL

import app.database as app_db
# Point the engine and sessionmaker to the temporary database
app_db.engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
app_db.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_db.engine)
app_db.SessionLocal.configure(bind=app_db.engine)

import app.main as app_main
app_main.engine = app_db.engine
app_main.SessionLocal = app_db.SessionLocal

from app.database import Base, get_db
from app.main import app

# Ensure tables exist in the temporary database
Base.metadata.create_all(bind=app_db.engine)

# Override FastAPI get_db dependency to yield sessions from the temporary database
def override_get_db():
    db = app_db.SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Clean up temp file on process exit
def _cleanup():
    try:
        app_db.engine.dispose()
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)
    except Exception:
        pass

atexit.register(_cleanup)

import pytest

@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """Session fixture confirming database isolation."""
    yield {
        "engine": app_db.engine,
        "SessionLocal": app_db.SessionLocal,
        "db_path": TEST_DB_PATH,
        "real_db_path": REAL_DB_PATH,
    }

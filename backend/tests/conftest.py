import pytest
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models import user, dataset, course_record, analysis, recommendation, scenario, audit  # noqa
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def test_client(db_engine):
    Session = sessionmaker(bind=db_engine)
    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers_admin(test_client, db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    if not session.query(User).filter(User.email == "admin@test.edu").first():
        user = User(email="admin@test.edu", hashed_password=hash_password("AdminPass123"), full_name="Test Admin", role=UserRole.admin, is_active=True)
        session.add(user)
        session.commit()
    session.close()
    resp = test_client.post("/api/auth/login", json={"email": "admin@test.edu", "password": "AdminPass123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def auth_headers_scheduler(test_client, db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    if not session.query(User).filter(User.email == "scheduler@test.edu").first():
        user = User(email="scheduler@test.edu", hashed_password=hash_password("SchedulerPass123"), full_name="Test Scheduler", role=UserRole.academic_scheduler, is_active=True)
        session.add(user)
        session.commit()
    session.close()
    resp = test_client.post("/api/auth/login", json={"email": "scheduler@test.edu", "password": "SchedulerPass123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import main  # noqa: E402
from app.db import Base, get_db  # noqa: E402


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}", connect_args={"check_same_thread": False}
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()
    engine.dispose()
    os.unlink(path)


def test_create_and_list_schedule(client):
    r = client.post("/api/schedules", json={"name": "S1", "mode": "day", "start_date": "2026-01-01"})
    assert r.status_code == 201
    sid = r.json()["id"]
    r = client.get("/api/schedules")
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())


def test_task_crud(client):
    s = client.post("/api/schedules", json={"name": "S", "mode": "day", "start_date": "2026-01-01"}).json()
    r = client.post(f"/api/schedules/{s['id']}/tasks", json={"name": "T1", "start_offset": 0, "duration": 3})
    assert r.status_code == 201
    tid = r.json()["id"]
    r = client.patch(f"/api/tasks/{tid}", json={"duration": 5})
    assert r.status_code == 200
    assert r.json()["duration"] == 5
    r = client.delete(f"/api/tasks/{tid}")
    assert r.status_code == 204


def test_dependency_and_cycle(client):
    s = client.post("/api/schedules", json={"name": "S", "mode": "day", "start_date": "2026-01-01"}).json()
    a = client.post(f"/api/schedules/{s['id']}/tasks", json={"name": "A", "duration": 2}).json()
    b = client.post(f"/api/schedules/{s['id']}/tasks", json={"name": "B", "duration": 2}).json()
    c = client.post(f"/api/schedules/{s['id']}/tasks", json={"name": "C", "duration": 2}).json()

    # B depends on A
    r = client.post(f"/api/tasks/{b['id']}/dependencies", json={"prerequisite_id": a["id"]})
    assert r.status_code == 201
    # C depends on B
    r = client.post(f"/api/tasks/{c['id']}/dependencies", json={"prerequisite_id": b["id"]})
    assert r.status_code == 201
    # A depends on C -> cycle
    r = client.post(f"/api/tasks/{a['id']}/dependencies", json={"prerequisite_id": c["id"]})
    assert r.status_code == 400
    # self-dependency
    r = client.post(f"/api/tasks/{a['id']}/dependencies", json={"prerequisite_id": a["id"]})
    assert r.status_code == 400


def test_cross_schedule_dependency_rejected(client):
    s1 = client.post("/api/schedules", json={"name": "S1", "mode": "day", "start_date": "2026-01-01"}).json()
    s2 = client.post("/api/schedules", json={"name": "S2", "mode": "day", "start_date": "2026-01-01"}).json()
    a = client.post(f"/api/schedules/{s1['id']}/tasks", json={"name": "A"}).json()
    b = client.post(f"/api/schedules/{s2['id']}/tasks", json={"name": "B"}).json()
    r = client.post(f"/api/tasks/{a['id']}/dependencies", json={"prerequisite_id": b["id"]})
    assert r.status_code == 400

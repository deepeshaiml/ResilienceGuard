import asyncio
from pathlib import Path

import httpx
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db import Base, get_db
from app.main import app


def setup_client(tmp_path, monkeypatch):
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(test_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(test_engine)
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(get_settings(), "restore_root", tmp_path / "restore")


def test_http_workflow_requires_human_approval_and_records_restore(tmp_path, monkeypatch):
    setup_client(tmp_path, monkeypatch)

    async def exercise_workflow():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/api/actions", json={"scenario_id": "ransomware", "service_id": "clinical-db", "backup_id": "bkp-db-20261026-0700"})
                assert response.status_code == 409

                response = await client.post("/api/actions", json={"scenario_id": "physical-disaster", "service_id": "clinical-db", "backup_id": "bkp-db-20261026-0500"})
                assert response.status_code == 200
                action = response.json()
                assert action["status"] == "pending"
                assert not list((tmp_path / "restore").glob("**/*.json"))

                rejected = await client.post(f"/api/actions/{action['id']}/decision", json={"decision": "reject", "rationale": "Not this time"})
                assert rejected.status_code == 200
                assert rejected.json()["status"] == "rejected"
                assert not list((tmp_path / "restore").glob("**/*.json"))

                approved_proposal = (await client.post("/api/actions", json={"scenario_id": "physical-disaster", "service_id": "clinical-db", "backup_id": "bkp-db-20261026-0500"})).json()
                approved = await client.post(f"/api/actions/{approved_proposal['id']}/decision", json={"decision": "approve", "rationale": "Sandbox evidence test"})
                assert approved.status_code == 200
                assert approved.json()["status"] == "completed"
                assert approved.json()["result"]["checksum_match"] is True
                assert Path(tmp_path / "restore" / approved_proposal["id"] / "restored-clinical-db.json").is_file()
                events = (await client.get("/api/audit")).json()
                assert {event["event_type"] for event in events} >= {"proposal_created", "human_rejected", "human_approved", "restore_completed"}
                report = await client.get("/api/report.pdf?scenario_id=physical-disaster")
                assert report.status_code == 200 and report.content.startswith(b"%PDF")

    try:
        asyncio.run(exercise_workflow())
    finally:
        app.dependency_overrides.clear()

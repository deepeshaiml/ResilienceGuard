from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .assistant import advise
from .config import get_settings
from .data import backup_by_id, load_data, scenario_by_id, service_by_id
from .db import Base, SessionLocal, engine, get_db
from .engine import assess
from .models import AuditEvent, RecoveryAction, utcnow
from .report import build_report
from .restore import RestoreDenied, run_approved_restore
from .schemas import ActionDecisionIn, ActionProposalIn, AssistantRequest


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    get_settings().restore_root.mkdir(parents=True, exist_ok=True)
    load_data()
    yield


app = FastAPI(title="ResilienceGuard API", version="0.1.0", description="Synthetic recovery readiness assessment and approved sandbox restore workflow", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _action_dict(action: RecoveryAction) -> dict:
    result = json.loads(action.result_json) if action.result_json else None
    return {
        "id": action.id,
        "scenario_id": action.scenario_id,
        "service_id": action.service_id,
        "backup_id": action.backup_id,
        "operation": "sandbox_restore",
        "status": action.status,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "decided_at": action.decided_at.isoformat() if action.decided_at else None,
        "completed_at": action.completed_at.isoformat() if action.completed_at else None,
        "duration_seconds": action.duration_seconds,
        "result": result,
    }


def _successful_restores(db: Session) -> dict[str, dict]:
    result: dict[str, dict] = {}
    actions = db.scalars(select(RecoveryAction).where(RecoveryAction.status == "completed").order_by(RecoveryAction.completed_at.desc())).all()
    for action in actions:
        if action.service_id not in result:
            result[action.service_id] = {"status": "completed", "backup_id": action.backup_id, "action_id": action.id, "duration_seconds": action.duration_seconds, "result": json.loads(action.result_json or "{}")}
    return result


def _assessment(scenario_id: str, db: Session) -> dict:
    try:
        return assess(scenario_id, successful_restores=_successful_restores(db))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "resilienceguard-api", "data": "synthetic"}


@app.get("/api/scenarios")
def scenarios() -> list[dict]:
    return load_data()["scenarios"]


@app.get("/api/assessment")
def assessment(scenario_id: str = Query(...), db: Session = Depends(get_db)) -> dict:
    return _assessment(scenario_id, db)


@app.post("/api/assistant")
def assistant(request: AssistantRequest, db: Session = Depends(get_db)) -> dict:
    result = _assessment(request.scenario_id, db)
    return advise(result, request.question)


@app.post("/api/actions")
def propose_action(request: ActionProposalIn, db: Session = Depends(get_db)) -> dict:
    if scenario_by_id(request.scenario_id) is None:
        raise HTTPException(status_code=404, detail="Unknown scenario")
    service = service_by_id(request.service_id)
    backup = backup_by_id(request.backup_id)
    if service is None or backup is None or backup["service_id"] != request.service_id:
        raise HTTPException(status_code=404, detail="Unknown service or backup")
    current = _assessment(request.scenario_id, db)
    service_row = next(row for row in current["services"] if row["id"] == request.service_id)
    backup_row = next((row for row in service_row["backups"] if row["id"] == request.backup_id), None)
    if not backup_row or not backup_row["usable"]:
        raise HTTPException(status_code=409, detail="Selected backup is missing, inaccessible, corrupted, or untrusted for this scenario")
    action = RecoveryAction(id=str(uuid4()), scenario_id=request.scenario_id, service_id=request.service_id, backup_id=request.backup_id, status="pending")
    db.add(action)
    db.flush()  # Persist the referenced row before inserting its audit event (required by PostgreSQL FK ordering).
    db.add(AuditEvent(action_id=action.id, event_type="proposal_created", detail_json=json.dumps({"operation": "sandbox_restore", "human_decision_required": True})))
    db.commit()
    db.refresh(action)
    return _action_dict(action)


@app.post("/api/actions/{action_id}/decision")
def decide_action(action_id: str, request: ActionDecisionIn, db: Session = Depends(get_db)) -> dict:
    try:
        decision = request.validated_decision()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    action = db.get(RecoveryAction, action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    if action.status != "pending":
        raise HTTPException(status_code=409, detail=f"Action is already {action.status}; decisions are single-use")
    action.decided_at = utcnow()
    if decision == "reject":
        action.status = "rejected"
        db.add(AuditEvent(action_id=action.id, event_type="human_rejected", detail_json=json.dumps({"rationale": request.rationale})))
        db.commit()
        return _action_dict(action)

    action.status = "approved"
    db.add(AuditEvent(action_id=action.id, event_type="human_approved", detail_json=json.dumps({"rationale": request.rationale, "operation": "sandbox_restore"})))
    db.commit()
    try:
        result = run_approved_restore(action)
        action.duration_seconds = result["duration_seconds"]
        action.output_relpath = result["output_relpath"]
        action.status = "completed" if result["status"] == "passed" else "failed"
        action.completed_at = utcnow()
        action.result_json = json.dumps(result)
        db.add(AuditEvent(action_id=action.id, event_type="restore_completed" if result["status"] == "passed" else "restore_failed", detail_json=json.dumps({"evidence_id": result["evidence_id"], "checksum_match": result["checksum_match"], "sandbox_only": True})))
        db.commit()
    except (RestoreDenied, OSError, ValueError) as exc:
        action.status = "failed"
        action.completed_at = utcnow()
        action.result_json = json.dumps({"status": "failed", "detail": str(exc), "sandbox_only": True})
        db.add(AuditEvent(action_id=action.id, event_type="restore_failed", detail_json=json.dumps({"detail": str(exc)})))
        db.commit()
    db.refresh(action)
    return _action_dict(action)


@app.get("/api/actions")
def actions(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(RecoveryAction).order_by(RecoveryAction.created_at.desc())).all()
    return [_action_dict(row) for row in rows]


@app.get("/api/audit")
def audit_events(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(100)).all()
    return [{"id": row.id, "action_id": row.action_id, "event_type": row.event_type, "occurred_at": row.occurred_at.isoformat(), "detail": json.loads(row.detail_json)} for row in rows]


@app.get("/api/actions/{action_id}/download")
def download_restore(action_id: str, db: Session = Depends(get_db)) -> FileResponse:
    action = db.get(RecoveryAction, action_id)
    if action is None or action.status != "completed" or not action.output_relpath:
        raise HTTPException(status_code=404, detail="No completed restore output is available")
    root = get_settings().restore_root.resolve()
    path = (root / action.id / Path(action.output_relpath).name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Restore output is missing")
    return FileResponse(path, media_type="application/json", filename=path.name)


@app.get("/api/report.pdf")
def report_pdf(scenario_id: str = Query(...), db: Session = Depends(get_db)) -> Response:
    content = build_report(_assessment(scenario_id, db))
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="ResilienceGuard-{scenario_id}-assessment.pdf"'})


def create_tables_for_tests() -> None:
    Base.metadata.create_all(bind=engine)

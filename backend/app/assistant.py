"""Evidence-constrained advisory. It can summarize a plan but cannot execute tools."""

from __future__ import annotations

import json
from typing import Any

import httpx

from .config import get_settings


def _rule_summary(assessment: dict[str, Any], question: str) -> dict[str, Any]:
    scenario = assessment["scenario"]
    metrics = assessment["metrics"]
    blocked = [row for row in assessment["services"] if row["status"] == "unavailable" and row["recovery_status"] == "blocked"]
    ready = [row for row in assessment["services"] if row["status"] == "unavailable" and row["recovery_status"] == "ready"]
    refs = sorted({item["id"] for item in assessment["evidence"]})
    blocked_names = ", ".join(row["name"] for row in blocked) or "none"
    ready_names = ", ".join(row["name"] for row in ready) or "none"
    recommendations = [
        {"action_id": row["service_id"], "text": f"Review the {row['service']} recovery proposal using {row['evidence_id']}; a human must approve any sandbox restore."}
        for row in assessment["recovery_plan"] if row["status"] == "ready"
    ]
    return {
        "mode": "deterministic_fallback",
        "summary": f"For {scenario['name']}, {metrics['blocked_services']} unavailable service(s) are blocked ({blocked_names}); {metrics['ready_to_recover']} are ready for a constrained sandbox test ({ready_names}).",
        "recommendations": recommendations,
        "uncertainties": [
            "Malware scanning was not performed; every malware status remains unknown.",
            "Configured restore durations are estimates until a sandbox restore is measured.",
            "The recovery sample uses synthetic JSON files, not a live hospital application or database engine.",
        ],
        "evidence_ids": refs,
        "question_received": question,
        "execution_authority": "none",
    }


def _ask_local_model(assessment: dict[str, Any], question: str, url: str, model: str) -> dict[str, Any] | None:
    allowed_evidence = {item["id"] for item in assessment["evidence"]}
    allowed_actions = {item["service_id"] for item in assessment["recovery_plan"] if item["status"] == "ready"}
    facts = {
        "scenario": assessment["scenario"]["name"],
        "metrics": assessment["metrics"],
        "services": [{"id": s["id"], "name": s["name"], "status": s["status"], "recovery_status": s["recovery_status"], "blockers": s["recovery_blockers"], "rpo_gap_seconds": s["rpo_gap_seconds"], "backup_evidence_id": s["selected_backup_evidence_id"]} for s in assessment["services"]],
        "baseline_plan": assessment["recovery_plan"],
        "assurance_notes": assessment["assurance_notes"],
    }
    prompt = (
        "You are an advisory-only resilience report writer. Use only the supplied JSON facts. "
        "Do not invent facts, clean malware verdicts, change the deterministic plan, or call tools. "
        "Return strict JSON with keys summary (string), recommendations (array of objects with action_id and text), "
        "uncertainties (array of strings), evidence_ids (array). Every action_id must be one of "
        f"{sorted(allowed_actions)} and every evidence_id must be one of {sorted(allowed_evidence)}. "
        "Keep recommendations advisory and require human approval. Question: " + question + "\nFACTS=" + json.dumps(facts)
    )
    try:
        response = httpx.post(
            url.rstrip("/") + "/api/generate",
            json={"model": model, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0}},
            timeout=httpx.Timeout(35.0, connect=1.0),
        )
        response.raise_for_status()
        outer = response.json()
        candidate = json.loads(outer.get("response", ""))
        if not isinstance(candidate.get("summary"), str) or not isinstance(candidate.get("recommendations"), list):
            return None
        if not set(candidate.get("evidence_ids", [])).issubset(allowed_evidence):
            return None
        if not all(isinstance(item, dict) and item.get("action_id") in allowed_actions for item in candidate["recommendations"]):
            return None
        if not isinstance(candidate.get("uncertainties", []), list):
            return None
        return {
            "mode": "local_llm_advisory",
            "summary": candidate["summary"],
            "recommendations": candidate["recommendations"],
            "uncertainties": candidate.get("uncertainties", []),
            "evidence_ids": candidate["evidence_ids"],
            "question_received": question,
            "execution_authority": "none",
            "model": model,
        }
    except (httpx.HTTPError, ValueError, TypeError, KeyError):
        return None


def advise(assessment: dict[str, Any], question: str) -> dict[str, Any]:
    settings = get_settings()
    if settings.ollama_url:
        model_result = _ask_local_model(assessment, question, settings.ollama_url, settings.ollama_model)
        if model_result:
            return model_result
    return _rule_summary(assessment, question)

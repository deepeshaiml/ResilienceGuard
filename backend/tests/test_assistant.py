from app.assistant import advise
from app.engine import assess


def test_fallback_is_deterministic_evidence_referenced_and_advisory():
    result = advise(assess("physical-disaster"), "What should happen next?")
    assert result["mode"] == "deterministic_fallback"
    assert result["execution_authority"] == "none"
    assert set(result["evidence_ids"]).issubset({"BK-001", "BK-002", "BK-003", "BK-004", "BK-005", "MISS-directory-store", "SC-001"} | {item["id"] for item in assess("physical-disaster")["evidence"]})
    assert all(item["action_id"] in {row["service_id"] for row in assess("physical-disaster")["recovery_plan"] if row["status"] == "ready"} for item in result["recommendations"])
    assert any("malware" in item.lower() for item in result["uncertainties"])

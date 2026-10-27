from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.restore import RestoreDenied, run_approved_restore


def test_pending_action_cannot_run_restore(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "restore_root", tmp_path)
    pending = SimpleNamespace(status="pending", scenario_id="physical-disaster", service_id="clinical-db", backup_id="bkp-db-20261026-0500", id="safe-test-id")
    with pytest.raises(RestoreDenied, match="human-approved"):
        run_approved_restore(pending)
    assert list(tmp_path.iterdir()) == []


def test_approved_restore_copies_and_verifies_synthetic_sample(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "restore_root", tmp_path)
    approved = SimpleNamespace(status="approved", scenario_id="physical-disaster", service_id="clinical-db", backup_id="bkp-db-20261026-0500", id="safe-test-id")
    result = run_approved_restore(approved)
    output = tmp_path / "safe-test-id" / "restored-clinical-db.json"

    assert result["status"] == "passed"
    assert result["sandbox_only"] is True
    assert result["production_modified"] is False
    assert result["checksum_match"] is True
    assert result["source_sha256"] == result["restored_sha256"]
    assert result["fixture_health"]["status"] == "passed"
    assert result["fixture_health"]["database_engine_tested"] is False
    assert output.is_file()
    assert result["duration_seconds"] >= 0
    assert result["malware_status"] == "unknown"


def test_corrupted_backup_is_denied_even_after_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "restore_root", tmp_path)
    approved = SimpleNamespace(status="approved", scenario_id="ransomware", service_id="clinical-db", backup_id="bkp-db-20261026-0700", id="safe-bad-id")
    with pytest.raises(RestoreDenied, match="corrupted"):
        run_approved_restore(approved)
    assert list(tmp_path.iterdir()) == []

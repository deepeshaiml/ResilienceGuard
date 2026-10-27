#!/usr/bin/env python3
"""Normalize the actual pip-audit and npm-audit JSON outputs for the report."""

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
artifacts = root / "artifacts"
python_audit = json.loads((artifacts / "pip-audit.json").read_text(encoding="utf-8"))
npm_audit = json.loads((artifacts / "npm-audit.json").read_text(encoding="utf-8"))
python_vulns = sum(len(item.get("vulns", [])) for item in python_audit.get("dependencies", []))
npm_vulns = npm_audit.get("metadata", {}).get("vulnerabilities", {}).get("total", 0)
if python_vulns or npm_vulns:
    raise SystemExit(f"Unresolved dependency findings: pip-audit={python_vulns}, npm audit={npm_vulns}")

summary = {
    "snapshot": "2026-10-26",
    "python": {
        "tool": "pip-audit 2.10.1",
        "target": "backend/requirements-dev.txt and resolved dependencies",
        "audited_packages": len(python_audit.get("dependencies", [])),
        "vulnerability_findings": python_vulns,
        "summary": "0 known vulnerabilities found",
    },
    "npm": {
        "tool": "npm audit",
        "target": "frontend/package-lock.json",
        "audited_packages": npm_audit.get("metadata", {}).get("dependencies", {}).get("total", 0),
        "vulnerability_findings": npm_vulns,
        "summary": "0 findings",
    },
    "remediation_history": [
        "Initial npm audit identified high severity image-size parser advisories through PptxGenJS; image-size was pinned to patched 2.0.3 and the lockfile was re-audited.",
        "Initial pip-audit identified CVE-2025-71176 in pytest 8.4.2; the development pin was upgraded to pytest 9.0.3 and tests and the full dev dependency audit were rerun.",
    ],
    "limitations": "Point-in-time dependency advisory scans only; no full SAST, container image scan, penetration test, or runtime security certification.",
}
(artifacts / "security-results.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2))

# ResilienceGuard Technical Design

**Version:** MVP 0.1.0 · **Research and implementation snapshot:** 26 October 2026 · **Data:** fixed-seed synthetic fixtures

## Quick read

ResilienceGuard checks recovery evidence for important services. It does not store enterprise backups or decide by itself that production recovery is safe. Rules check whether a sample copy exists, how old it is, whether its file fingerprint matches, whether its location is reachable, and whether the systems it depends on can return. A person must approve the only restore operation in this demo: copying a registered synthetic file into a separate test folder.

**Example:** the demo clock says 08:00. The newest clinical database file is from 07:00 but was changed, so its SHA-256 fingerprint does not match. A 05:00 file in the West location does match, but it is three hours old against a two-hour data-loss target. That is one hour outside the target. The hospital application is still blocked because the inventory has no backup record for the directory data that its identity service needs. No malware scan has run, and the application itself has not been restored.

**Short glossary:** RPO (recovery point objective) is the maximum data age an organization accepts losing; RTO (recovery time objective) is its target time to resume service. SHA-256 is a file fingerprint, not a malware scan. A dependency is something a service needs. A failure domain is a place or resource that could be lost together. A sandbox is an isolated test area. For a plain-language walkthrough, see [AUDIENCE_GUIDE.md](AUDIENCE_GUIDE.md); for an AI integration example, see [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md).

## Product scope

ResilienceGuard is a recovery-readiness and evidence layer. It inventories backup metadata, compares file digests with an inventory manifest, applies scenario failure domains, checks service dependencies, proposes a recovery sequence, and records sandbox-only restore evidence. It does not provide enterprise backup, malware detection, production restore, disaster coordination, or regulatory certification.

## Architecture and selected technologies

See [architecture SVG](ResilienceGuard_Architecture.svg). The implementation choices below are pinned in the project. The installed host stack was Python 3.12.13, Node.js 26.9.0, npm 11.19.1, Docker 29.6.2, and Compose 5.3.1. Compose uses Python 3.12.13 and Node.js 24.22.1 LTS; Vite 8 requires Node 20.19+ or 22.12+, so Node 24 satisfies its engine floor. Package pins were checked against official release/package metadata on the research date; automated advisory scans are recorded in the evaluation report.

| Component | Selected version | Role | License / decision |
|---|---:|---|---|
| Python | 3.12.13 host and `python:3.12.13-slim-bookworm` container | API and data tooling | PSF License; supported runtime with broad dependency compatibility |
| FastAPI | 0.161.1 | REST API and OpenAPI | MIT; async-capable API surface |
| Pydantic | 2.14.0 | Request/response validation | MIT; strict bounded input validation |
| SQLAlchemy | 2.1.6 | Action/audit persistence | MIT; PostgreSQL and SQLite dialects |
| PostgreSQL | 18.6 Alpine image | Compose persistence | PostgreSQL License; stable supported major, patch release |
| NetworkX | 3.5 | Directed service dependency graph | BSD-3-Clause; small DAG with transparent deterministic traversal |
| React / React DOM | 19.3.1 | Dashboard and workflow UI | MIT |
| TypeScript | 5.9.3 | UI types | Apache-2.0 |
| Node.js | 24.22.1 LTS container; 26.9.0 host used for build | UI runtime | MIT; container uses supported LTS |
| Vite | 8.3.5 | Local dev server and build | MIT; Node engine requirement satisfied by Node 26 |
| `@vitejs/plugin-react` | 6.1.2 | React JSX integration | MIT; peer requirement Vite 8 |
| PptxGenJS | 4.0.1 | PowerPoint generation | MIT; requested deck tooling |
| python-docx | 1.2.0 | DOCX idea document | MIT |
| ReportLab | 4.4.6 | Evidence/business/evaluation PDFs | BSD-style license |
| Ollama (optional) | 0.40.11 | Local inference endpoint | MIT; current stable release at the 26 October 2026 snapshot; optional because model download and acceleration needs vary |
| Qwen3 8B (optional) | `qwen3:8b` | Advisory summary | Apache-2.0 model card; confirm model card and organizational approvals before deployment |

Python runtime pins are in `backend/requirements.txt`; document generation and test dependencies are in `backend/requirements-dev.txt` (pytest 9.0.3 includes the fix for CVE-2025-71176). JavaScript pins are in `frontend/package.json` and lockfile. PptxGenJS 4.0.1's transitive `image-size` parser is overridden to patched 2.0.3; the deck build and npm audit were rerun with this lock. PostgreSQL is only used for app state; synthetic backup files remain local filesystem fixtures. No S3-compatible service is necessary for this MVP.

### Alternatives considered

- **MinIO:** not selected. Its upstream `minio/minio` GitHub repository is archived read-only as of 25 April 2026 and the upstream marks the community repository unmaintained. The project is not dependent on object storage. For a later S3-backed connector, evaluate maintained alternatives such as SeaweedFS and Garage directly for S3 API coverage, operational model, license, security advisories, and patch cadence before deployment; do not treat them as drop-in equivalents without interoperability testing.
- **LangGraph:** not selected. The MVP has one explicit propose → human decision → constrained copy workflow persisted in SQLAlchemy. A graph-agent runtime would add complexity without materially improving this fixed approval path. NetworkX is used for the service dependency graph, not agent orchestration.
- **vLLM:** not selected for local demo. The host hardware is not assumed to have a compatible accelerator; Ollama offers a simple optional local endpoint. The deterministic fallback is the validated default.
- **Authenticated manifests:** not used. A single synthetic SHA-256 reference catches accidental/sample-file alteration but is not an authenticity guarantee if both data and manifest can be changed. Production requires signed manifests or protected key storage and immutability controls outside this MVP; a private signing key must not be shipped with fixtures.
- **OpenTelemetry:** not introduced. Structured persisted audit events plus application logs are adequate for the single-process demo. A production deployment should add OpenTelemetry trace/metric export with protected, privacy-reviewed telemetry.

## Research basis and market context

- **NIST SP 1339, OT Backup Quick Start Guide (June 2026):** states that OT backups support recovery from reliability and cyber incidents and emphasizes regular creation, change-management integration, recurring restore tests on non-production systems, and integrity checks before restore. The MVP reflects that separation with an isolated test and explicit integrity state. [NIST SP 1339](https://csrc.nist.gov/pubs/sp/1339/final)
- **NIST SP 800-34 Rev. 1:** guidance for information-system contingency planning, impact priorities, recovery strategies, and integration with broader emergency/continuity plans. It dates from 2010 and is guidance, not a current product certification. [NIST publication page](https://csrc.nist.gov/pubs/sp/800/34/r1/upd1/final)
- **NIST CSF 2.0:** the Recover function includes incident recovery planning and execution; ResilienceGuard is a narrow evidence aid, not a CSF conformity assessment. [NIST CSF 2.0](https://www.nist.gov/cyberframework)
- **NATO 2026 Resilience Baseline Requirements:** published September 2026; covers critical government services, energy, communications, transport, food/water, and the capacity to prepare, resist, respond, and recover. It highlights cyber and physical threats, extreme weather, strategic dependencies, cascading effects, exercises and restoration capability. ResilienceGuard is relevant to the continuity/recovery evidence theme but has no NATO affiliation or endorsement. [NATO official text](https://www.nato.int/en/about-us/official-texts-and-resources/official-texts/2026/09/15/2026-resilience-baseline-requirements)

### Existing offerings

Rubrik describes cyber recovery simulations, recovery plans, isolated environments, threat containment, recovery progress and compliance reporting. Veeam Recovery Orchestrator documents orchestration, readiness checks, isolated test labs, malware scans, RPO/RTO dashboards and reports. Cohesity markets clean-room response/recovery, cyber vaulting, isolated investigation, and recovery orchestration. These vendors already address substantial parts of the recovery problem. Differentiation is therefore a **proposed** positioning: lightweight, vendor-independent evidence normalization and scenario readiness across backup sources, combining cyber, physical and concurrent disruptions for smaller critical-service operators. The MVP demonstrates only a local synthetic dataset, not vendor integrations or market superiority.

Sources: [Rubrik Cyber Recovery](https://www.rubrik.com/products/cyber-recovery), [Veeam Recovery Orchestrator overview](https://helpcenter.veeam.com/docs/vro/userguide/overview.html), [Cohesity Clean Room](https://www.cohesity.com/solutions/clean-room/).

## Data and deterministic logic

The generator `scripts/generate_synthetic_data.py` uses a fixed seed (`20261026`) and fixed assessment time (`2026-10-26T08:00:00Z`). Files in `data/` include four service records, eight infrastructure assets, five backup records, SHA-256 manifest values embedded per backup, two backup locations, and three scenario overlays. Synthetic JSON payloads carry `fixture: true`, a schema version, a record count, and records marked synthetic.

Each backup record yields separate attributes:

1. **Existence:** does the expected fixture file exist?
2. **Freshness:** is its age at or under the service's configured RPO?
3. **Integrity:** does its SHA-256 digest match the recorded manifest?
4. **Location reachability:** is the backup's site available in this scenario?
5. **Trust/malware:** scenario trust can explicitly exclude a known bad point; malware scanning is absent, so cleanliness remains `unknown` for all copies.
6. **Restore outcome:** `not_tested` until an approved sandbox run records a measured result.

The dependency DAG uses service edges for Hospital Care Coordination → Clinical Records Database + Clinical Identity, and Clinical Identity → Directory Data Store. Database and directory recovery also require recovery storage/network. A service marked unavailable is recoverable only if it has a present, integrity-verified, reachable, scenario-trusted candidate and all unavailable service/infrastructure dependencies can be satisfied. A service not affected by the active scenario remains operational and need not be restored. Topological ordering is deterministic. Unknown or cyclic dependencies fail validation rather than being guessed.

RPO gap is calculated against the selected eligible snapshot. RTO gaps compare configured estimated restore seconds with target until an observed sandbox result exists; the UI/report label estimates. No measured duration is fabricated. The restore duration is monotonic-clock wall time for file copy, hash verification, and sample shape check; it is not a workload recovery RTO.

## API and persistence

Key endpoints: `GET /api/health`, `/api/scenarios`, `/api/assessment?scenario_id=...`; `POST /api/assistant`; `POST /api/actions`; `POST /api/actions/{id}/decision`; `GET /api/actions`, `/api/audit`; `GET /api/actions/{id}/download`; `GET /api/report.pdf?scenario_id=...`.

SQLAlchemy persists a one-time state machine (`pending → rejected` or `pending → approved → completed/failed`) and audit entries. The approval endpoint revalidates the source metadata, scenario eligibility, source digest, and action status. The restore routine rejects pending actions, rejects corrupted or scenario-untrusted files, and limits input to the checked-in synthetic backup directory. It writes to an action-ID subdirectory under `RESTORE_ROOT`; no client-supplied path or command is accepted. API listener ports bind to `127.0.0.1` in Compose.

The browser operator is the human approval gate in this single-user demo. There is no account authentication, role separation, CSRF/session model, multi-operator quorum, or production identity provider. A deployed system must add authenticated identities, policy enforcement, independent approval/quorum and tamper-resistant audit before operational use.

## Governed AI design

The rule engine owns eligibility, graph blockers, recovery order, and operation permissions. The optional local model sees a compact assessment and allowed action/evidence IDs; its prompt forbids new facts or actions, and its response is accepted only if it parses as JSON and cites IDs from the supplied set. The response cannot call a tool. The model can still produce unsupported natural-language text; it is labeled advisory and requires human review. When Ollama is absent, times out, or returns an invalid response, a deterministic rule-based summary is returned. LangGraph is omitted because the persisted linear approval state machine has no branching agent tool orchestration that needs checkpoints.

The selected optional model runtime is Ollama 0.40.11 and Qwen3 8B (`qwen3:8b`, Apache-2.0 as listed in its model card). Ollama 0.40.11 was the latest stable upstream release on 26 October 2026, published on 24 October. It is not included in the default container path or required for the MVP. The project does not make measured claims about Qwen3 accuracy; validation of a specific model/runtime/hardware configuration remains future evaluation. [Ollama releases](https://github.com/ollama/ollama/releases)

## Security and safety boundaries

- No production credentials, connector, backup-control API, command runner, or destructive tool exists.
- Source fixtures mount read-only in Docker; restore output is a different named volume.
- SHA-256 compare is a tamper/change detector relative to a reference. It proves neither provenance nor malware cleanliness.
- The synthetic fixture parser check is not a live database health check.
- A scenario label cannot authorize a restore on its own: each action requires a pending proposal and explicit human approval, then backend eligibility and hash checks.
- Input uses bounded Pydantic strings; origin/method CORS policy is restricted to the local UI; restore paths are canonicalized and confined.
- Compose demo database credentials are hard-coded convenience credentials and must never be reused outside a disposable local demo.
- Build dependencies are pinned; advisory scan results and container build results are recorded in the evaluation report. A clean scan at one time does not establish future safety.

## Delivery and current limitations

Run via `docker compose up --build`; API docs at `/docs`. Direct host execution uses a SQLite file. The synthetic catalog and scenario timestamps are fixed for reproducibility. Current MVP has four services and one missing-directory-backup gap. It tests a file-level JSON restore to a sandbox, not a VM/application/SQL database recovery. No antivirus/EDR, immutable storage, signed manifest, vendor adapter, live failure-domain discovery, telemetry export, RBAC, independent approver, or cloud/air-gapped deployment profile is implemented.

## Primary technology and source references

- FastAPI releases: https://github.com/fastapi/fastapi/releases
- Pydantic releases: https://github.com/pydantic/pydantic/releases
- SQLAlchemy releases: https://github.com/sqlalchemy/sqlalchemy/releases
- NetworkX releases: https://github.com/networkx/networkx/releases
- PostgreSQL release notes: https://www.postgresql.org/docs/release/
- React changelog: https://github.com/facebook/react/blob/main/CHANGELOG.md
- Vite release notes: https://github.com/vitejs/vite/blob/main/docs/releases.md
- Node.js releases: https://github.com/nodejs/node/releases
- Ollama releases/license: https://github.com/ollama/ollama/releases and https://github.com/ollama/ollama/blob/main/LICENSE
- Qwen3 model card: https://huggingface.co/Qwen/Qwen3-8B
- PptxGenJS license: https://github.com/gitbrent/PptxGenJS/blob/master/LICENSE
- MinIO repository status and security advisories: https://github.com/minio/minio and https://github.com/minio/minio/security

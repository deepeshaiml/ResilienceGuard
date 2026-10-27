# ResilienceGuard

## In plain language

ResilienceGuard helps answer: **if a serious disruption happened, which important services could we bring back, and what would stop us?** It checks sample backup copies and the systems that depend on one another. A human can then approve a real test copy into a separate folder.

For example, the demo can find an older database copy whose fingerprint matches, but flag that it is an hour older than the team's target. It can also show that the hospital application cannot return because its identity system needs a directory backup that is missing. That is a clear test result: **the data copy may be tested, but the complete service is still blocked.**

Start with the [audience guide](AUDIENCE_GUIDE.md) for a worked example and glossary, or the [demo guide](DEMO_GUIDE.md) to run the walkthrough. AI integrations should follow the [AI Agent Guide](AI_AGENT_GUIDE.md).

## What this MVP does

The local-first MVP uses repeatable rules to check whether synthetic backup files exist, are within their age target, match a saved SHA-256 fingerprint (a compact file fingerprint), and remain reachable during the selected scenario. It also identifies missing service requirements, proposes a recovery order, records human approval, and reports the result of a real isolated file copy. See the [glossary](AUDIENCE_GUIDE.md#short-glossary) for recovery-point and recovery-time targets (RPO/RTO) and other terms.

> This is a synthetic demonstration. It is not a backup product, malware scanner, production recovery service, or compliance attestation. Malware status stays unknown even when a hash matches.

## Run the application

### Docker Compose

Requirements: Docker Engine/Desktop with Compose v2.

```bash
docker compose up --build
```

Open <http://localhost:5173>. FastAPI docs are at <http://localhost:8000/docs>. The UI and API bind to localhost. Compose starts PostgreSQL 18.6, the API and the Vite UI. Synthetic fixtures mount read-only; approved restore outputs and database state use separate named volumes.

If those ports are already in use, Docker can assign free localhost ports: run `RG_WEB_PORT=0 RG_API_PORT=0 docker compose up --build -d`, then use `docker compose port web 5173` and `docker compose port api 8000` to see the assigned URLs. You can also set either variable to a specific free port.

Stop the application with `Ctrl+C` or `docker compose down`. `docker compose down -v` also removes database, restore and API state volumes.

### Run API and UI directly

Requirements: Python 3.12 and Node.js 22.12+; Node 24 LTS is recommended. The Compose images pin Python 3.12.13 and Node 24.22.1.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

The default local API database is `artifacts/resilienceguard.db` (SQLite). Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL to use PostgreSQL instead. `scripts/start_local.sh` starts the API; `scripts/start_ui.sh` starts the UI.

## Demo walkthrough

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for a judge-ready walkthrough, expected synthetic findings, scenario switches, and restore approval steps.

## Core capabilities

- Three repeatable scenarios: primary data-center loss, ransomware with a corrupted/untrusted latest database copy, and a concurrent power/network failure plus loss of one backup location.
- Separate backup state for **existence**, **freshness**, **SHA-256 integrity**, **malware status**, and **restore test outcome**.
- Service-dependency map for the hospital application, clinical database, identity service, directory data, recovery storage and network. It shows which prerequisite blocks another service.
- Human approval or rejection for a sandbox-only copy operation, with persisted decision and audit events.
- Actual synthetic JSON file copy to an isolated directory, followed by source/destination fingerprint comparison and a basic file-shape check. This does not restore a PostgreSQL database or start the hospital application.
- Downloadable PDF assessment and restored fixture file.
- Optional local Ollama / Qwen3 advisory summary; deterministic fallback works without a model.

## Synthetic data

`scripts/generate_synthetic_data.py` uses seed `20261026` and an explicit `as_of` timestamp to regenerate all data under `data/`. It creates four services, five backup metadata records, sample JSON files, one altered database snapshot, a missing directory-store backup, three scenarios, dependencies, backup locations, RPO/RTO targets, and evidence IDs. Values are invented and contain no patient or customer data.

## Tests and security checks

```bash
.venv/bin/pytest -q backend/tests
cd frontend && npm run build
```

Security dependency scans can be run with `pip-audit` and `npm audit`. The technical design and evaluation report record the scans and test results completed for this submission. No test is a substitute for deployment security review.

## Optional local model

The core application works without a model. For a local Ollama install, download the Apache-2.0 Qwen3 8B model (`ollama pull qwen3:8b`) and set `OLLAMA_URL` / `OLLAMA_MODEL` for the API. For the optional Compose profile, set `OLLAMA_URL=http://ollama:11434`, start with `docker compose --profile llm up --build`, then run `docker compose exec ollama ollama pull qwen3:8b`. The request includes only the current synthetic evidence summary. The assistant has no action tools and the API validates response evidence/action IDs. Model-generated text still needs human review.

## Project documents

- [Technical design](ResilienceGuard_Technical_Design.md)
- [Quick guide and glossary](AUDIENCE_GUIDE.md)
- [AI agent safety and example](AI_AGENT_GUIDE.md)
- [Idea document (DOCX)](ResilienceGuard_Idea_Document.docx)
- [Idea document (PDF)](ResilienceGuard_Idea_Document.pdf)
- [Eureka pitch deck (PPTX)](ResilienceGuard_Pitch_Deck.pptx)
- [Eureka pitch deck (PDF)](ResilienceGuard_Pitch_Deck.pdf)
- [Business review deck (PPTX)](ResilienceGuard_Business_Review.pptx)
- [Business review deck (PDF)](ResilienceGuard_Business_Review.pdf)
- [Business case (PDF)](ResilienceGuard_Business_Case.pdf)
- [Evaluation report (PDF)](ResilienceGuard_Evaluation_Report.pdf)
- [Architecture diagram](ResilienceGuard_Architecture.svg)

### Rebuild the Business Review deck

The builder leaves its retained template unchanged and writes `ResilienceGuard_Business_Review.pptx` in the project root. It uses the local Codex template cache by default; if that reference is not available in your environment, provide its location explicitly:

```bash
python3 scripts/build_business_review.py --template /path/to/reference.pptx
```

## License

Project source is provided for hackathon evaluation. Component license summaries and their official sources are in the technical design. Synthetic data and generated submission materials may be reused with attribution to the project.

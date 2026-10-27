# ResilienceGuard Demo Guide

## 1. Start

```bash
docker compose up --build
```

Open <http://localhost:5173>. Wait until the header shows **API connected**. This starts PostgreSQL, FastAPI, and the Vite application. All UI/API ports bind to localhost.

If these ports are occupied, let Docker choose free ports with `RG_WEB_PORT=0 RG_API_PORT=0 docker compose up --build -d`, then check them with `docker compose port web 5173` and `docker compose port api 8000`.

If Docker is unavailable, follow the direct-run instructions in `README.md`; that uses SQLite instead of PostgreSQL.

## 2. A simple explanation for the audience

You can introduce the demo with this:

> “A backup job can finish successfully and still leave a service impossible to recover. This demo checks whether a copy exists, whether it is recent enough, whether the file matches its saved fingerprint, whether its storage site is still available, and whether the service has all the systems it needs. We will approve one synthetic file test and inspect what it proves—and what it does not prove.”

**RPO** means the maximum age of data the organization is willing to lose. **RTO** means the target time for getting a service running again. The demo shows configured targets and estimates; its millisecond file-copy time is not a hospital application RTO.

## 3. Show the physical-disaster scenario

The default scenario is **Primary data center lost**. Point out the amber synthetic-data banner and the separate evidence states.

Expected fixture facts:

- Four critical services are inventoried; the scenario marks the hospital app, clinical database, identity service, and directory store unavailable.
- Five backup records exist across two named locations. There is no backup record for Directory Data Store.
- `bkp-db-20261026-0700` exists and is fresh but fails SHA-256 because the sample fixture was deliberately altered.
- `bkp-db-20261026-0500` matches its saved SHA-256 fingerprint but is stale against the clinical database's two-hour RPO. At the demo time of 08:00 it is three hours old, so it is one hour beyond the target. Its recovery copy is in the West vault, outside the failed East/primary failure domain.
- Clinical Identity has a recent hash-verified copy, but identity recovery is blocked by its unavailable Directory Data Store dependency and the missing backup.
- Hospital Care Coordination is blocked by the identity dependency. The deterministic sequence puts prerequisites before the application.
- Malware scan status is **Not performed / unknown** for every record. Hash verification is not a malware verdict.

Explain the distinction: **the database copy is eligible for a supervised test, but it has not been restored yet. The hospital application is still blocked because identity depends on a directory store with no backup record.**

Switch to **Ransomware and untrusted snapshot**. The latest database copy is marked scenario-untrusted and its file hash fails. The older West vault snapshot is the eligible fallback, with a visible RPO gap. The currently available identity service does not need a new backup restore in this scenario.

Switch to **Concurrent power and network disruption**. The East vault is unavailable with the primary site; the West vault and independent recovery network remain available. The graph and backup-location evidence are recalculated for that combined disruption.

## 4. Run an actual isolated restore

1. In **Sandbox recovery approval**, select **Clinical Records Database**.
2. Select `bkp-db-20261026-0500` (the most recent verified, reachable candidate in the physical-disaster scenario). The candidate shows fresh/stale, integrity, location, evidence ID, and malware unknown separately.
3. Select **Prepare proposal**. The action remains pending; no file is copied yet.
4. Select **Approve sandbox restore**. The backend revalidates that the source is registered, the scenario permits it, the status is human-approved, and the hash still matches.
5. Review the actual result: bytes copied, measured elapsed duration, source/destination SHA-256 match, JSON fixture structure check, malware unknown, and explicit note that no PostgreSQL engine/application was restored.
6. Select **Download restored file** to inspect the copied JSON. The output is in a UUID-named subdirectory of the isolated restore volume.

The API contains no production connectors. The restore function accepts only approved actions and fixture paths and writes below its configured restore root.

## 5. Evidence report and audit

Select **Export assessment** to download the scenario-specific evidence PDF. It includes summary counts, per-service status, configured RPO/RTO gaps, recovery sequence, assurance limits, and evidence IDs. The `/api/audit` endpoint records proposal, approval/rejection, and restore completion/failure events.

## 6. Optional local model

The **Recovery brief** button returns an evidence-grounded deterministic summary by default. To use a local Qwen3 8B instance:

```bash
ollama pull qwen3:8b
```

For a host-installed Ollama, set `OLLAMA_URL=http://host.docker.internal:11434` for the Compose API. To run the optional Compose runtime instead, start with `OLLAMA_URL=http://ollama:11434 docker compose --profile llm up --build`, then run `docker compose exec ollama ollama pull qwen3:8b`. For an API started directly on the host, use `OLLAMA_URL=http://localhost:11434`. The model is optional, adds hardware/runtime needs, and has no recovery execution tools.

## 7. Stop and reset

```bash
docker compose down
```

For a clean database and restore volume before another demo:

```bash
docker compose down -v
docker compose up --build
```

This deletes only the local demonstration's named Docker volumes.

## AI agent example

If an AI agent is helping a judge or operator, ask it to explain the current findings, cite IDs from the assessment, list unknowns, and suggest a human-reviewed next step. For example:

> “Summarize the physical-disaster scenario for a hospital operations lead. Explain the one-hour data-age gap, identify the missing directory backup, state that malware status is unknown, cite evidence IDs, and do not approve or run an action.”

See [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md) for a safe response example and strict approval boundary. The optional model is advisory; the deterministic rules and human decision control the workflow.

# AI Agent Guide

## Purpose

This guide helps an AI assistant or automation agent explain a ResilienceGuard assessment accurately. The product's rules decide backup eligibility, dependency blockers, and recovery order. An AI may summarize those results, point out uncertainty, and suggest a human-reviewed test.

**An AI agent must not approve or execute a recovery.** The demo assistant has no recovery tools. The approval screen and API are separate human-controlled workflow features.

## Safe reading workflow

1. Read the current scenario and its assessment from `GET /api/scenarios` and `GET /api/assessment?scenario_id=<scenario-id>`.
2. Explain each claim using evidence IDs returned in that assessment. Do not invent an ID or infer missing evidence.
3. Separate these facts: file exists, age versus target, fingerprint match, scenario trust, storage reachability, dependency readiness, malware scan, and actual restore result.
4. State what is unknown. In this MVP, malware scanning is never performed. A ready-to-test label is not proof of a completed restore.
5. Recommend the smallest safe next step, such as asking an operator to review a missing dependency or proposing an isolated sample test.
6. Stop and wait for an authorized person to make any approval decision.

## Example request and answer

Request:

> Explain the primary data-center disaster assessment to a hospital operations lead. Cite evidence IDs, state the data-loss gap, list blockers and unknowns, and recommend a safe next step. Do not approve or run anything.

An acceptable response would say:

> The clinical database has a West-vault copy whose fingerprint matches the saved reference (`BK-003`). It is three hours old, one hour older than the configured two-hour recovery-point target. The hospital application is blocked because its identity service needs Directory Data Store, and the inventory has no backup record for that store (`MISS-directory-store`). The scenario is `SC-001`. Malware status is unknown because no scanner ran, and no live application restore was tested. Ask the recovery owner to review the missing directory backup and, if appropriate, approve a synthetic database copy into the isolated test folder. No action has been approved or run.

This answer distinguishes a **candidate that may be tested** from a successful restore, and it distinguishes file integrity from malware cleanliness.

## Output format for integrations

An integrating agent can use a small structured summary such as:

```json
{
  "summary": "The clinical database has a verified West-vault copy, but it is one hour older than its two-hour target. The hospital application is blocked by the missing Directory Data Store backup.",
  "evidence_ids": ["SC-001", "BK-003", "MISS-directory-store"],
  "unknowns": ["Malware scan not performed", "Live application/database restore not tested"],
  "recommended_next_step": "Ask the recovery owner to review the missing directory backup and consider a separately approved sandbox test.",
  "action_taken": "none"
}
```

Use evidence IDs present in the current API response. The IDs above belong to the checked-in synthetic example; they may differ if the inventory changes.

## Actions and approval boundary

- `GET` assessment, scenario, evidence, and report endpoints are for reading.
- `POST /api/assistant` asks for an advisory summary; it cannot execute an action.
- `POST /api/actions` creates a pending sandbox proposal. Only create one when a user asks to prepare a proposal.
- `POST /api/actions/{id}/decision` changes the decision and can start the constrained file copy. **Never call it unless an authorized human explicitly approves that exact proposal.** A general request to “analyze,” “plan,” “recommend,” or “prepare” is not approval.
- The demo restore only reads the registered synthetic fixtures and writes beneath the configured isolated restore root. It is not a production recovery interface.

## Claims agents must avoid

- “The backup is clean” based only on a matching hash.
- “The service has been restored” based only on `ready`, `usable`, or a proposed action.
- “The RTO was met” based on a JSON file-copy duration.
- “The plan is safe for production” based on this synthetic demo.
- Any statement unsupported by the current scenario assessment or its evidence IDs.

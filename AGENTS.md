# ResilienceGuard Workspace Instructions

- Keep recovery decisions deterministic and evidence-backed; an LLM may explain and suggest but must never execute recovery actions.
- Sandbox restore operations may only read the checked-in synthetic fixtures and write beneath the configured isolated restore root.
- Label synthetic data and any simulated or estimated result clearly in the UI and documents.
- Never claim malware cleanliness from a hash match. Report existence, freshness, integrity, malware status, and restore success separately.
- Keep generated research claims linked to primary sources and mark business prices as illustrative assumptions.
- Run the requested automated checks before reporting measured results. Do not invent results.
- Keep PLAN.md, PROGRESS.md, ARCHITECTURE.md, README.md, and DEMO_GUIDE.md current.
- Write for both technical and non-technical readers: define acronyms on first use, explain technical labels in plain language, and include a concrete synthetic example where it clarifies a result.
- For AI agents, cite current evidence IDs, state what is unknown, and treat analysis or a recommendation as no approval to act.

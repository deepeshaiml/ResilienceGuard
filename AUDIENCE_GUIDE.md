# ResilienceGuard: a quick guide for people and AI agents

## The idea in one minute

ResilienceGuard helps a team answer a practical question: **if a disaster happened today, which important services could we bring back, and what would stop us?**

It checks whether example backup files exist, how old they are, whether their SHA-256 fingerprint matches the saved reference, whether their storage site is reachable in the chosen scenario, and whether required systems are available. A person can then approve a real copy of a synthetic file into an isolated test folder.

The demo uses invented hospital-style data. It does not connect to a real hospital, scan for malware, or restore a live database or application.

## A worked example

The demo clock is fixed at **08:00 UTC**. In the primary data-center disaster:

1. The newest clinical database copy is from 07:00, but its contents were deliberately changed. Its fingerprint no longer matches, so the system does not offer it as a trusted restore candidate.
2. The 05:00 copy in the West vault matches its saved fingerprint and the West vault is reachable. It is three hours old. The database's recovery-point target is two hours, so the copy is **one hour outside the target**. It may still be tested, but the extra data-loss risk must be visible.
3. The hospital application also needs the identity service. Identity needs the Directory Data Store. The inventory contains no Directory Data Store backup record, so the hospital application remains blocked even though the database copy can be tested.
4. A matching fingerprint only tells us that the file matches its saved reference. No malware scan ran, so malware status stays **unknown**.

In plain language: **one database copy is available for a supervised test, but it is older than the target; the hospital service is still blocked because a required directory backup is missing. Nothing here proves the data is malware-free or that the hospital application has been restored.**

## What the status words mean

| Status | Plain-language meaning |
|---|---|
| Present | A record or file was found. This alone does not prove it is usable. |
| Fresh | The copy is within the configured data-loss target. |
| Stale | The copy is older than that target. It may be usable but may leave a gap. |
| Integrity verified | The file's SHA-256 fingerprint matches the saved value. This does not prove who made it or that it is malware-free. |
| Untrusted | The selected scenario excludes the copy, for example because it was marked affected by ransomware. |
| Ready to test | The copy and required dependencies pass the demo's rules. No restore has happened yet. |
| Restore passed | The synthetic file was actually copied into the isolated folder and its fingerprint and JSON shape checks passed. This is not a live application or database recovery. |
| Malware unknown | No malware scanner was run. This is the expected state for every demo backup. |

## Short glossary

- **Backup / recovery copy:** a saved copy of data that may be used to rebuild a service.
- **Manifest:** the inventory record that stores the expected fingerprint and facts about a copy.
- **SHA-256 fingerprint / hash:** a compact file fingerprint. A mismatch means the file differs from the saved reference; a match is not a malware clearance.
- **RPO, recovery point objective:** the maximum age of data the organization says it can afford to lose. Here the clinical database target is two hours.
- **RTO, recovery time objective:** the target time for getting a service running again. The demo's configured estimates are not a measured application recovery time.
- **Dependency:** something a service needs. The hospital application needs its database and identity service.
- **Failure domain:** things that could be lost together, such as one building, power supply, network, or storage site.
- **Sandbox / isolated test folder:** a separate place to test a copy without changing production systems.
- **Evidence ID:** a short reference such as `BK-003` or `MISS-directory-store` that lets a reader trace a statement to an inventory observation.
- **Deterministic:** the same inventory and scenario produce the same rule-based result.

## Who should read what

- **Business and public-sector leaders:** start with the [README](README.md), this example, and the [business case](ResilienceGuard_Business_Case.pdf). Prices and customer counts in the business case are assumptions, not market quotes.
- **Operators and evaluators:** use the [demo guide](DEMO_GUIDE.md) to switch scenarios and approve the isolated sample restore.
- **Engineers and security reviewers:** read the [technical design](ResilienceGuard_Technical_Design.md), [architecture overview](ARCHITECTURE.md), and [evaluation report](ResilienceGuard_Evaluation_Report.pdf).
- **AI agents:** follow [AI_AGENT_GUIDE.md](AI_AGENT_GUIDE.md). Treat the assessment as evidence to explain; never treat it as authority to approve or run a recovery.

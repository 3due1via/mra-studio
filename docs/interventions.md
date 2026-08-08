# Interventions workflow

BUILD 005 introduces persistent maintenance work orders backed by PostgreSQL.

- Codes use the `intervention_code_seq` sequence and have the form `INT-000001`. Sequence values are concurrency-safe but intentionally not gap-free: rollbacks can consume numbers.
- Creation retries are identified by `client_request_id`; transitions use `command_id`. SHA-256 fingerprints are stored only in PostgreSQL and are never returned by the API or written to audit events.
- PATCH uses optimistic locking through `expected_version`. Transitions additionally lock the intervention row with `SELECT FOR UPDATE`.
- Operational timeline events are separate from the security audit and are append-only through a PostgreSQL trigger. A completed resolution is copied to the timeline before an administrator reopens the intervention.
- `completed` interventions cannot be patched or linked to Knowledge until reopened. `cancelled` interventions are terminal and immutable.
- Summary `recently_completed` means completed during the previous 30 days, evaluated in UTC.
- Viewer can read; editor can create, edit, perform ordinary transitions and manage Knowledge links; admin can additionally cancel and reopen.
- Operational notes are normalized and checked with a best-effort credential detector. Notes must never contain passwords, tokens, cookies, API keys, authorization headers or database URLs.

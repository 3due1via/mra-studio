# Audit trail

MRA Studio records security and domain mutations in `audit_events`. A successful domain change and its event share one PostgreSQL transaction. The table is application-level append-only and a PostgreSQL trigger also rejects direct `UPDATE` and `DELETE` statements.

The event payload is built from per-entity allowlists and passed through a bounded recursive sanitizer. Passwords, tokens, cookies, authorization values, database URLs, request headers, exception details, SQL, IP addresses, and user agents are never recorded. A server-generated request UUID correlates events without trusting client identifiers.

Only administrators can read the audit endpoints and `/activity` route. There are no API operations for mutating or exporting events.

Pagination uses the immutable `(occurred_at, id)` keyset. The opaque cursor includes a fingerprint of the active filters and is rejected if reused with a different filter set. Events inserted after the first page that sort before its cursor are intentionally visible on a fresh traversal, not injected into later pages; this prevents duplicates and unstable page boundaries.

Retention duration, historical anonymization, export, hash chaining, SIEM integration, webhooks, notifications, and analytics remain explicit decisions for a later build. They are intentionally outside BUILD 004.

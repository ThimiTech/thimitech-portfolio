# Phase 4: audit and organization monitoring

## Contract

- `/app/audit` and `/app/monitoring`, and their APIs, require `super_admin`. HR, managers, employees, guests, and anonymous callers cannot read them.
- Audit events record actor ID/name/role snapshots, create/update/delete/membership action, model/object ID, changed fields, time, source, entry point, and a server-generated correlation ID.
- Concrete business models across all existing domains are tracked. Ordinary saves/deletes and many-to-many changes use model signals. Existing business bulk-write paths are instrumented explicitly. Read acknowledgements and internal email-claim timestamps are excluded as noise.
- Passwords, tokens, contact details, free-form bodies/notes, attachments, salary amounts, invoice rates, asset costs, and payment references are never copied into audit diffs. Their changed field names are retained with a redaction marker. New model fields default to redaction.
- Unsafe API requests use one transaction for business changes and audit rows. Failed requests roll back both. Scheduled absence marking identifies itself as a system job. Context is cleared after each request/job.
- Audit rows cannot be edited/deleted through the API, Django admin, model/queryset methods, or ordinary PostgreSQL UPDATE/DELETE statements. Database owners can still alter schema/triggers; this is not a claim of tamper-proof storage against database administrators.
- The audit begins on installation; no historical events are fabricated. No backfill or external analytics service is introduced.
- Audit search is paginated and validates filters, dates, module, actor IDs, and correlation IDs. Search covers actor name, model label, and exact record ID. Request bodies, query strings, credentials, and client IPs are not stored. Public diff strings/collections are bounded and marked when truncated.

## Monitoring definitions

- Headcount: current active staff, grouped by department and role; include unassigned staff and recent joiners.
- Attendance: configurable past window, up to 93 days; use the attendance module's existing day classification and status derivation against the current active roster. Respect join dates, weekends, mandatory holidays, approved leave, and today's incomplete check-ins. Attendance percentage uses only working-day present/late/absent entries.
- Leave exposure: current calendar-year paid leave quota, approved usage, pending requests, and remaining days. Use existing year-splitting rules. Unlimited types have no numeric remaining balance. No cash liability is estimated without a cash-out policy.
- Project health: current active projects, task completion, overdue tasks, missing assignments, and explicit complete/at-risk/on-track/unplanned states. Archived projects are excluded from current health.
- Finance: existing all-period totals, grouped by currency; no mixed-currency addition. Inventory: current availability and overdue returns. Each panel states its time basis.
- Show audit capture start and recent changes. A successful read must not itself create audit events.

## Verification

Backend tests cover role boundaries, JWT actor attribution, redaction, no-op saves, membership and bulk writes, rollback, context isolation, append-only guards including PostgreSQL, filters/pagination, and monitoring calculations. Frontend tests cover audit diff rendering, empty/error states, and attendance chart data. Check migrations, OpenAPI, type checking, production build, scoped lint, and real browser behavior at desktop and mobile sizes.

## Local acceptance results — 17 October 2026

- Backend: full PostgreSQL-backed regression suite passed (191 tests); includes 17 Phase 4 tests. Latest boundary-date and deletion-lock changes also covered by a focused audit rerun.
- Frontend: 18 tests passed across four files, including seven Phase 4 tests. Vue/TypeScript checking, scoped ESLint, and production build passed.
- Migration consistency check: no pending model changes. Audit migrations applied to the local development database.
- OpenAPI generation and validation: zero errors. Existing user serializer type-hint warnings and a status enum naming warning remain. Production bundling retains the existing terrain scene size warning; oversight pages are lazy-loaded independently.
- Browser: verified desktop and 390px mobile layouts, exact daily attendance table, live audit actor/before/after values, request tracing, and empty finance state. No browser warnings/errors observed. A temporary department rename was restored; its two audit events remain as the verification record.

## Operations and extension notes

- Apply migrations before serving the new API. Existing Celery workers must restart to load the instrumented absence job and audit signal registrations. Standard application restart loads middleware and signals.
- Audit rows are operational history and can grow continuously. No automatic purge is installed. Back up the audit table with the business database; choose a retention/archive policy before introducing a purge process.
- Django signals do not observe arbitrary SQL or future `QuerySet.update`, `bulk_update`, or `bulk_create` calls. Existing business bulk paths have explicit capture. Future bulk mutation paths must use the audit helper or emit audit events inside the same transaction. A future external writer needs its own integration.
- Sensitive fields default to redaction. Review additions to the public-field allowlist explicitly. This trail is append-only at the application and ordinary SQL layers; a database owner can alter triggers/schema or truncate tables.
- Attendance uses the current active roster and current calendar policy for the selected period, rather than historical employee/policy snapshots. The endpoint caps the period at 93 days. Leave exposure applies current paid leave quotas to current active staff and follows existing stored-day/year-splitting rules; it does not estimate payroll cash liability.

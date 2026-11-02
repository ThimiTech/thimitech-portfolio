# Thimi Tech — Portfolio + Organization Operating Platform

This repo is evolving from a public **portfolio website** into **Thimi Tech OS**:
a single product with three faces —

1. **Public portfolio** (marketing, project showcase) — *exists today*.
2. **Recruitment** — public job listings + apply; applicants become enrolled users — *partly exists*.
3. **Internal operations** — authenticated employee / manager / HR / admin platform:
   attendance, leave, calendar, notice board, org & staff profiles, project management,
   Jira-style workflow, finance/salary, inventory, auditing, org monitoring — *to be built*.

> The internal app lives in the **same Vue app** under authenticated `/app/*` routes
> (not a separate SPA). The public site stays at `/`.

---

## Current architecture (verified working locally)

| Layer | Stack |
|-------|-------|
| Backend | Django 6.1 + Django REST Framework, SimpleJWT auth, drf-spectacular (OpenAPI) |
| DB | PostgreSQL **17** (Django 6.1 requires PG ≥ 15) |
| Frontend | Vue 3 + Vite 8 + Tailwind CSS 4 + Pinia + vue-router |
| Auth | JWT, **email is the login field** (`USERNAME_FIELD = 'email'`) |

### Backend layout (`backend/`)
- `config/` — settings, urls, wsgi/asgi. Env-driven via `python-dotenv` (`.env`).
- `apps/users/` — custom `User` (email login), registration.
- `apps/services/`, `apps/projects/`, `apps/team/`, `apps/jobs/` — portfolio + recruitment content.
- `apps/permissions/permissions.py` — `IsAdminOrReadOnly`.
- **View style today:** function-based views with `@api_view` + `@extend_schema`. Serializers are `ModelSerializer`.
  *(New modules should move to DRF `ViewSet` + routers — see Conventions.)*

### Frontend layout (`frontend/src/`)
- `pages/` (routed) + `components/` (sections). `router/index.ts`, `stores/auth.ts` (localStorage JWT).
- API client: `src/api/api.ts` (axios, `/api/` base, token refresh interceptor). The legacy `src/api.js` was removed.
- API base is relative `/api/`; dev requests are proxied to Django by Vite (see `vite.config.ts`).

---

## Local development

### One-click start (recommended)
- **Windows:** double-click `start-dev.bat` in the repo root.
- **Linux/macOS:** `./start-dev.sh` (first time: `chmod +x start-dev.sh`). Ctrl+C stops what it started.

Both scripts: create `backend/.env` from `.env.example` if missing → create the venv (uv, Python 3.13)
and sync `requirements.txt` → `backend/dev_check.py db` (creates the DB if missing; rejects PostgreSQL < 15)
→ `migrate` → on a fresh DB, create the admin and run `seed_dev.py` → start Redis (docker) → start
Django :8000, Celery worker + beat (only if Redis answers; otherwise `CELERY_TASK_ALWAYS_EAGER=True`),
and Vite :5173 → open the browser. Servers already listening on :8000/:5173 are left alone.
Named `start-dev.*` on purpose: `start` is a cmd builtin, so `start.bat` misparses when typed.

### Manual start

Prereqs on this machine: **Python 3.13 via `uv`**, Node 20+, PostgreSQL 17 on **port 5433**.

> Gotchas already resolved: Django 6.1 needs Python ≥ 3.12 and PostgreSQL ≥ 15.
> The local PG14 (port 5432) is too old; use **PG17 on 5433**.

### Backend
```bash
cd backend
# venv (uv, Python 3.13) — already created at .venv
uv pip install --python .venv -r requirements.txt

# .env (already present locally, git-ignored):
#   SECRET_KEY=...   DEBUG=True
#   DB_NAME=thimitech  DB_USER=postgres  DB_PASSWORD=postgres
#   DB_HOST=localhost  DB_PORT=5433

.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe seed_dev.py          # idempotent demo data
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```
Admin: `admin@thimitech.com` / `admin12345` (dev only). Django admin at `/admin/`,
API docs at `/api/docs/`.

### Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api and /media to :8000)
```

---

## Conventions for new work

- **Roles live on the User**, not scattered booleans. Add `User.role` (choices below) + keep
  Django `is_staff`/`is_superuser` for admin-site access. Gate APIs with small DRF permission
  classes in `apps/permissions/` (e.g. `IsManager`, `IsHROrAdmin`), not inline checks.
- **New apps use `ViewSet` + `DefaultRouter`** under `apps/<name>/`, with `@extend_schema`
  tags per app so `/api/docs/` stays organized. Keep serializers thin; push logic to models/services.
- **One app = one domain** (`attendance`, `leave`, `calendar`, `notices`, `org`, `pm`, `finance`,
  `inventory`, `audit`). Register under `apps.<name>` and include urls in `config/urls.py`.
- **Timestamps + soft context:** use `auto_now_add`/`auto_now`; record `created_by` where it aids auditing.
- **Frontend:** authenticated area under `src/pages/app/` with a nested route + layout; a
  route guard reads the role from the auth store and hides/redirects. Reuse `api/api.ts`.
- **Money:** `DecimalField(max_digits=12, decimal_places=2)`, never float.
- **Migrations are committed.** Run `makemigrations` per app; don't edit applied migrations.

---

## Role model (access control)

Five tiers, ascending. Stored as `User.role`; each tier implies the ones below for read access
unless a module says otherwise.

| Role | Who | Can |
|------|-----|-----|
| `guest` | Public / applicant | Portfolio, job listings, apply, own application status |
| `employee` | Staff | Own attendance, leave requests, calendar, notices, own profile, assigned project tasks |
| `manager` | Team lead | Team's attendance/leave **approval**, team project boards, team reports |
| `hr_admin` | HR / Finance | Hiring pipeline, all staff profiles, leave policy, salary/finance, inventory |
| `super_admin` | Owner | Everything incl. org config, auditing, monitoring, user/role management |

Applicants who are hired are promoted `guest → employee` (keeps one user table).

---

## Build roadmap

### Phase 1 — **now** (employee daily-use core)
Modules: **Attendance + Leave + Holidays/Calendar** and **Notice board + Org/Staff profiles**.

Proposed apps & models (sketch — refine in each app's planning):

- `apps/org/`
  - `Organization` (name, logo, about, links[github/web/youtube], founded, ...)
  - `Department` (name, parent → self for hierarchy, manager → User)
  - `EmployeeProfile` (OneToOne User; department, title, join_date, phone, address, emergency_contact, photo, skills)
- `apps/attendance/`
  - `AttendanceRecord` (user, date, check_in, check_out, status[present/late/absent/wfh], source)
  - `WorkSchedule` (user/dept, weekly expected hours) — feeds "late/absent" derivation
- `apps/leave/`
  - `LeaveType` (name, paid, annual_quota)
  - `LeaveBalance` (user, leave_type, remaining)
  - `LeaveRequest` (user, type, start, end, reason, status[pending/approved/rejected], approver, decided_at)
- `apps/calendar_app/`
  - `Holiday` (date, name, recurring) · `CalendarEvent` (title, start, end, audience[org/dept/user], created_by)
- `apps/notices/`
  - `Notice` (title, body, audience, pinned, publish_at, expires_at, author) · `NoticeRead` (notice, user, read_at)

Phase 1 API surface (illustrative): `POST /api/attendance/check-in|check-out`,
`GET /api/attendance/me`, `POST /api/leave/requests`, `POST /api/leave/requests/{id}/decision`
(manager+), `GET /api/calendar/`, `GET /api/notices/`, `GET/PATCH /api/org/profile/me`,
`GET /api/org/structure`.

Phase 1 frontend: `/app` shell (sidebar by role) → dashboard, attendance, leave, calendar,
notices, directory, my-profile.

Public landing variants: `/` restores the pre-Codex landing page from Git; `/new`
preserves the redesigned landing page and its scroll-driven 3D scene. Original
components live in `frontend/src/components/original/` and original font/color
tokens are scoped in `frontend/src/assets/original.css`.

### Phase 2 — Project management + Jira-style workflow
`apps/pm/`: `Project`, `Board`, `Column`, `Task` (status/assignee/estimate/labels), `Comment`,
`Milestone`, repo/link hub (github, web URLs, youtube, docs). Visualizations: timeline (Gantt),
org/project progress dashboards.

### Phase 3 — Finance / Salary + Inventory
`apps/finance/`: `SalaryStructure`, `Payslip`, `Expense`, `Invoice`. `apps/inventory/`:
`Asset`, `Assignment`, `Category`. Role-gated to `hr_admin`+.

Phase 2 and Phase 3 implementation notes and acceptance contract: `PHASE_2_3.md`.
Routes: `/app/projects`, `/app/finance`, `/app/inventory`; APIs: `/api/pm/`, `/api/finance/`, `/api/inventory/`.
Payroll policy confirmed: monthly NPR with manual deductions. Payslips snapshot salary structures; issue/payment states preserve finalized amounts. Payments are recorded references, not bank transfers. Assets preserve assignment and return history.

### Phase 4 — Auditing + org monitoring
`apps/audit/`: append-only `AuditLog` (actor, action, target, diff, ts) written via DRF
signals/middleware. Admin dashboards: headcount, attendance trends, leave liability,
project health, finance summaries.

Implemented Phase 4 contract and verification: `PHASE_4.md`.
Super-admin routes: `/app/monitoring`, `/app/audit`. APIs: `/api/monitoring/overview/`,
`/api/audit/events/`, `/api/audit/options/`. Audit captures begin with installation;
existing history is not reconstructed. Sensitive diff values are redacted. PostgreSQL
triggers reject ordinary UPDATE/DELETE of audit rows. Leave exposure is reported in
days; no cash-out policy has been defined.

---

## Infra additions (decided: add now)

- **Celery + Redis** for async + scheduled work (`config/celery.py`; broker via `CELERY_BROKER_URL`,
  default `redis://localhost:6379/0`; local Redis = docker container `thimi-redis`).
  Schedules are static in `CELERY_BEAT_SCHEDULE` (settings) using Celery's default file scheduler.
  **Do not add `django-celery-beat`**: no release supports Django 6.1 (it pins `django<6.1` and
  silently downgrades Django). Current jobs: daily `mark_absentees`, 5-minute `email_due_urgent_notices`,
  leave-decision / notice emails via `apps.users.tasks.send_email`.
- **Email:** console backend in dev (already set); real SMTP via env in prod.
- Keep secrets in `.env` (git-ignored). Never commit real credentials.

---

## Operational notes (Phase 1)

- **Attendance capture** = manual check-in/out button. Client IP: `X-Forwarded-For` is trusted only when
  `REMOTE_ADDR` is a private/loopback proxy, and the right-most public hop wins (left hops are client-controlled).
  Production nginx must set `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` and reach Django over
  loopback/private network, or IPs fall back to the proxy address.
- **Notice attachments** are served only via `GET /api/notices/{id}/attachment/`. In production block direct access:
  `location /media/notices/ { internal; }`.
- **Celery**: `.delay()` only queues to Redis. Run a worker (`celery -A config worker --pool=solo -l info` on Windows)
  and beat, or set `CELERY_TASK_ALWAYS_EAGER=True` in `.env` for dev.
- **Windows**: set `PYTHONUTF8=1` for runserver and the worker; the console email backend otherwise raises
  `UnicodeEncodeError` on non-cp1252 text (names, leave reasons) and the email is dropped.
- Dashboard: `GET /api/dashboard/` (`apps/org/dashboard.py`) aggregates each module's own helpers
  (`attendance.views.today_payload`, `attendance.services.day_statuses`, `calendar_app.views.feed_items`, leave services,
  `NoticeViewSet` queryset). Change module logic there, not in the dashboard.
- **Urgent notices** are emailed exactly once, claimed via `Notice.emailed_at` (`notices.views.email_urgent`): at create
  when live, otherwise by beat task `apps.notices.tasks.email_due_urgent_notices` (every 5 min, looks back 1 day).
- **Passwords**: HR resets someone else's via `PATCH /api/org/people/{id}/ {password}` (same edit rights as other HR
  fields); everyone changes their own via `POST /api/org/people/me/password/ {current_password, new_password}`.
- **Delivery workspace** (`apps/pm`): tabs Overview · Board · Sprints · Timeline · Notes · Docs · Meetings · Whiteboard ·
  Links & milestones · Public profile · Settings (`/app/projects/:id?tab=`). Members create/edit notes, docs, meetings and
  whiteboards; only the owner or a project manager deletes. Only one sprint per project can be active (DB constraint).
  `Task.completed_at` is set in `Task.save()` and feeds the burndown. `[[wikilinks]]` resolve on the client
  (note → doc → task key → meeting). Markdown is rendered with marked + DOMPurify (`pm.ts renderMarkdown`).
  Whiteboard saves send `version`; a stale version gets 409. Whiteboards are excluded from the audit log.
- **Project documents** are served only via `GET /api/pm/documents/{id}/file/` (text is served as text/plain, with
  `CSP: sandbox`). In production block direct access: `location /media/pm/docs/ { internal; }`.
- **Public case studies**: `/work` and `/work/:slug` call `GET /api/pm/public/[slug/]` (no auth). A project shows up only
  when `visibility=public` and it is not archived. Only `public_sections` are exposed, and only links/docs marked `public`.
  Project meetings appear in the calendar feed (`kind: meeting`) for their attendees and creator.
- **Confirmations** in `/app` use `confirmDialog()` (`components/app/ui/confirm.ts`, host mounted in `AppLayout`), never
  `window.confirm`.
- Tests: `DB_TEST_NAME=test_thimi_<x> CELERY_TASK_ALWAYS_EAGER=True .venv/Scripts/python.exe manage.py test --noinput`.
- **Password reset**: `POST /api/password-reset/` (always 200) emails `{FRONTEND_URL}/reset-password?uid=&token=`;
  `POST /api/password-reset/confirm/` sets the password and blacklists every outstanding refresh token. Both are
  throttled (`THROTTLE_PASSWORD_RESET`, default 10/hour per IP). `POST /api/register/` returns `{access, refresh}`.
- **Notifications** (`apps/notifications`, not audited): modules call `notifications.services.push(users, kind, title,
  body, link)`; it runs in the caller's transaction. `GET /api/nav-counts/` feeds every shell badge (the layout polls
  it every 60 s); add new badge counts there, not as separate requests.
- **Server lists**: `config.pagination.ServerListMixin` adds `?page=&page_size=&search=&ordering=&status=` to a
  ViewSet. Paging is opt-in (only with `?page=`), so callers that expect a bare list keep working. Frontend:
  `useServerTable()` + `<DataTable :total>` (server mode).
- Frontend tests need Node 22 (`C:\Users\Admin\AppData\Local\nvm\v22.14.0`); Node 20 crashes vitest. npm 10 hits an
  arborist bug on this lockfile; use `npx -y npm@11 …` for installs/audit fixes.

## Repo housekeeping
- Two root `*.zip` snapshots and `backend/thimitech_backup.sql` are **legacy** (older
  single-`services`-app schema). Not restored into the current schema; kept for reference only.
  Content was re-seeded via `seed_dev.py`. Consider moving them out of the repo.

## Open questions (resolve as phases start)
- Payroll uses monthly NPR with manual deductions; automatic tax calculations are outside the current scope.
- Do managers map to `Department.manager`, or a separate team-membership table?

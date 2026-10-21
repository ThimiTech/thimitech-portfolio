# Security audit — Thimi Tech OS

Date: 2026-10-21. Scope: `backend/**` (every app in `backend/apps/`, `config/`), plus `frontend/src/api/api.ts` and
`frontend/src/stores/auth.ts`. Frontend pages, components, layouts and the router are out of scope; they were only
searched for `v-html` (none found).

**Result:** I fixed 13 issues. Four items need the owner's decision. Backend suite: **209 tests pass** (the 191
existing tests plus 18 new regression tests):
`DB_TEST_NAME=test_thimi_sec CELERY_TASK_ALWAYS_EAGER=True PYTHONUTF8=1 .venv/Scripts/python.exe manage.py test --noinput`.
`manage.py check --deploy` with `DEBUG=False` shows only the existing drf-spectacular schema warnings and the opt-in
HSTS preload warning.

## Findings

| # | Sev | Where | Issue and impact | Status | Proof |
|---|-----|-------|------------------|--------|-------|
| C1 | **Critical** (if the key was reused) | git history: `backend/.env` in commits `e15e7c0`, `056acf8`, `dd0193e` (pushed to `origin`) | The real `SECRET_KEY` and DB password were committed. SimpleJWT signs tokens with `SECRET_KEY`, so anyone who has the repo can forge a `super_admin` JWT on any server that uses that key. The current local key is different. I could not check production. | **Needs decision**: rotate the production `SECRET_KEY` and DB password now, unless you have confirmed they differ. Optionally purge the history with `git filter-repo`. Rotation is the actual fix. | — |
| H1 | High | `backend/thimitech_backup.sql:568` (tracked in git) | The dump contains the PBKDF2 hash of the superuser `admin`. It can be cracked offline if that password is still in use. | **Needs decision**: change that password everywhere, and remove the file from the repo (CLAUDE.md already calls it legacy). | — |
| H2 | High | `apps/org/serializers.py:36` (`validate_photo_file`) | The profile photo field is declared explicitly, so it skipped Django's image-extension validator. Pillow accepts image/HTML polyglots. Any employee could upload `x.html`, which `/media/` serves as `text/html` on the app's origin. That is stored XSS, and the attacker can read the victim's JWT from localStorage, including an HR or super-admin token. | Fixed: the extension must be an image type. | `org.tests…test_photo_polyglot_with_html_extension_rejected` |
| H3 | High | `apps/jobs/serializers.py:43-50`, `apps/jobs/models.py:8,67` | The CV upload accepted any file type and size, so any registered guest could do the same XSS as H2. CVs (personal data) were stored at guessable public paths: the first `cv.pdf` keeps that exact name. | Fixed: pdf/doc/docx only, 5 MB limit, stored under a random `applications/cv/<uuid>/` directory (migration `jobs/0006`). | `jobs.tests.ApplicationUploadTests` (4 tests) |
| H4 | High | `config/urls.py:36-48`, `apps/users/views.py:31`, `apps/org/views.py:194`, `apps/users/throttles.py` | There was no throttling on login, register, password change or token refresh, so online password brute force was unlimited. | Fixed: limits keyed on the real client IP using the existing proxy-aware `client_ip`. Login allows 10/min per IP+email and 60/min per IP, so a shared office NAT is not locked out. Register allows 10/hour, password change 5/min, refresh 60/min. All are env-tunable. | `users.tests…test_login_bruteforce_throttled`, `test_register_throttled`, `test_password_change_throttled` |
| H5 | High | `config/settings.py:216-224` | Refresh tokens lived 7 days with no rotation, no blacklist and no logout. An HR password reset or a password change left stolen tokens valid. | Fixed: refresh tokens now rotate and the old one is blacklisted (`token_blacklist` app). Added `POST /api/token/blacklist/` for logout. `CHECK_REVOKE_TOKEN` makes any password change revoke every existing token. Frontend changes: refresh is single-flight (parallel 401s cannot burn the rotated token), the rotated refresh token is stored, logout revokes server-side, and a 401 after a refresh ends the session. | `users.tests…test_refresh_rotates_and_old_refresh_is_blacklisted`, `test_logout_blacklists_refresh`, `test_password_change_revokes_existing_tokens` |
| M1 | Medium | `apps/users/serializers.py:18-41` | Registration (1) skipped `AUTH_PASSWORD_VALIDATORS`, so `12345678` was accepted; (2) allowed case-variant duplicate accounts (`Admin@…` and `admin@…`), which helps impersonation; (3) returned a 500 when two emails shared a local part. | Fixed. | `users.tests…test_weak_password_rejected`, `test_email_normalised_and_case_duplicates_rejected`, `test_username_collision_does_not_500`, `test_signup_is_always_guest` |
| M2 | Medium | `config/settings.py:31-33, 169-199` | Production posture: no HSTS, SSL redirect or Secure cookie flags; a missing or dev `SECRET_KEY` was not rejected; CORS allowed `localhost:5173` in production. | Fixed: everything is gated on `DEBUG=False`. HSTS is 1 year with subdomains. A weak or `dev-` key now stops startup. Dev CORS origins apply only when `DEBUG` is on. `nosniff`, `X-Frame-Options: DENY` and a referrer policy are set. | `check --deploy` (above). The startup guard was verified manually: it raises `ImproperlyConfigured`. |
| M3 | Medium | `apps/finance/views.py:15-29, 71-75, 117, 137` | Separation of duties: an `hr_admin` could create or raise **their own** salary, generate, issue or pay their own payslip, and approve or pay their own expense. Attendance and leave already forbid self-decisions. | Fixed: `forbid_self` returns 403 unless the user is `super_admin`. HR can still draft and submit their own expense. | `finance.tests.FinanceSeparationOfDutiesTests` (2 tests) |
| M4 | Medium | `config/settings.py:232` | `/api/schema/` and `/api/docs/` were public in production and mapped every internal endpoint. | Fixed: they require Django staff (session from `/admin/` or JWT) when `DEBUG` is off, and stay open in dev. | config |
| M5 | Medium | `config/settings.py:196-198` | Throttle counters used the per-process LocMem cache, so with N workers the effective limit becomes N times the configured one. | Fixed: setting `CACHE_URL=redis://…` switches to Redis, which already runs for Celery. **Set it in production.** | config |
| L1 | Low | `apps/jobs/serializers.py:43` | Applicants could apply to inactive or closed jobs by ID. | Fixed. | `jobs.tests…test_cannot_apply_to_inactive_job` |
| L2 | Low | `backend/media/applications/cv/*` (existing rows) | CVs uploaded before this fix still sit at the old guessable paths and are publicly served. | **Needs decision**: move them into random directories, or block `/media/applications/` in nginx. Blocking also breaks the admin's CV links, so it needs a small HR-only download endpoint like the one notices use. | — |
| L3 | Low | deps: `requirements.txt` | pip-audit: PyJWT 2.14.0 had 2 advisories. Pillow 12.3.0 has 8 CVEs, all fixed only in 13.0.0 (a major version). | PyJWT fixed (bumped to 2.15.0). Pillow is **Needs decision** (major upgrade; regression-test image uploads first). | pip-audit |
| L4 | Low | `frontend/package-lock.json` | `npm audit --omit=dev`: `follow-redirects` (axios dependency, runtime; credential-header leak on redirects) and `vite` 8.3.0–8.3.2 (`launch-editor`, dev server only) are both rated high. `npm audit fix` is non-breaking. | **Needs decision** (another agent owns the frontend package files): run `npm audit fix`. | npm audit |
| L5 | Low | `config/urls.py:61` | The Django admin is at the default `/admin/`. It is password-protected and now has HSTS and Secure cookies. | Accepted. Optionally restrict it by IP in nginx. | — |
| I1 | Info | `apps/attendance/services.py:client_ip` | `X-Forwarded-For` is trusted only when `REMOTE_ADDR` is private or loopback, and the right-most public hop wins. That is correct behind nginx. If Django is reachable directly from a LAN, LAN clients can spoof it. With a CDN in front, the CDN's IP wins. | Accepted. Bind gunicorn to `127.0.0.1`. | — |
| I2 | Info | `frontend/src/stores/auth.ts` | JWTs live in localStorage, so any XSS means token theft. H2 and H3 removed the known XSS vectors, and no `v-html` exists in `frontend/src`. | Accepted. Moving to httpOnly refresh cookies is a possible later hardening step. | grep |
| I3 | Info | `apps/leave/services.py:notify`, `apps/notices/views.py:email_urgent` | A user-controlled name or title goes into email subjects. Django rejects newlines in headers (`BadHeaderError`), so there is no injection; at worst that one email is dropped. | Accepted. | — |
| I4 | Info | `CHECK_REVOKE_TOKEN` rollout | Tokens issued before this deploy lack the new claim, so **everyone is logged out once** at deploy. Changing your own password also ends your session; the frontend logs you out. | Expected. | — |

### Checked and found sound (no change needed)

- **AuthZ and IDOR, per module:**
  - Attendance: self-service is scoped to the user; HR corrections forbid self-edits.
  - Leave: querysets are scoped, and `can_decide` / `can_cancel` are checked per object.
  - Notices: scoping is by audience and live state; only the author or HR can edit or see readers.
  - Calendar: `visible_events` / `visible_leaves`; only the creator or HR can write.
  - PM: `visible_projects` plus `require_manager`; assignees can only move their own tasks.
  - Finance, inventory, audit and monitoring: gated by role (HR+ for finance and inventory, super_admin for audit and monitoring).
- **Mass assignment and role escalation:** `role` and `is_staff` are read-only on `/api/me/`. `PersonSerializer` checks edit rights before validating, allows only self-editable fields for yourself, lets HR grant only guest/employee/manager, and protects super admins and superusers. Signup cannot set a role (now covered by tests).
- **Injection:** no raw SQL, `.extra()`, `mark_safe` or `eval` (only parameterised SQL in audit tests). CSV exports neutralise formulas. Notice bodies are plain text.
- **Notice attachments:** extension allowlist, 10 MB limit, random directory, served only through the scoped `…/attachment/` endpoint as a download.
- **Audit:** append-only (PostgreSQL triggers), sensitive values redacted, no request bodies or IPs stored.
- **Celery tasks** take no attacker-controlled arguments.
- Inactive users are rejected on both access and refresh.

## Production deployment checklist

**Environment (`backend/.env`, never committed):**

- `DEBUG=False`
- `SECRET_KEY=<new 50+ char random value>` (see C1). Generate one with `python -c "import secrets;print(secrets.token_urlsafe(50))"`.
- `DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT`, with a rotated password.
- `CACHE_URL=redis://localhost:6379/1` (shared throttle counters).
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, plus `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` and `DEFAULT_FROM_EMAIL`.
- Optional: `THROTTLE_LOGIN`, `THROTTLE_LOGIN_IP`, `THROTTLE_REGISTER`, `THROTTLE_PASSWORD`, `THROTTLE_TOKEN_REFRESH`, `SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`.

**Deploy steps:**

- Run `manage.py migrate`. This adds the `token_blacklist` tables and `jobs.0006`.
- Run `manage.py check --deploy`.
- Restart gunicorn, the Celery worker and beat.
- Schedule `manage.py flushexpiredtokens` daily with cron. It prunes the blacklist tables.

**nginx:**

```nginx
server_tokens off;
client_max_body_size 12m;                       # largest upload is a 10 MB notice attachment

location /api/ { proxy_pass http://127.0.0.1:8000; include proxy_django; }
location /admin/ { proxy_pass http://127.0.0.1:8000; include proxy_django; }   # optionally: allow <office IP>; deny all;

# proxy_django:
proxy_set_header Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;   # right-most hop = real client (see I1)
proxy_set_header X-Forwarded-Proto $scheme;                    # overwrite, never pass the client's through
                                                               # (else SECURE_SSL_REDIRECT loops)

location /media/notices/ { internal; }          # served only via /api/notices/{id}/attachment/
location /media/ {
    alias /path/to/backend/media/;
    add_header X-Content-Type-Options nosniff always;
    add_header Content-Security-Policy "default-src 'none'; img-src 'self'; sandbox" always;  # no script even if a bad file slips in
}
# location /media/applications/ { internal; }   # only once an HR CV download endpoint exists (see L2)
```

- Bind gunicorn to `127.0.0.1` only (I1). Serve TLS only and redirect port 80 to 443.
- After the first deploy, consider adding the domain to the HSTS preload list and setting `SECURE_HSTS_PRELOAD = True`.

## Owner decisions needed

1. **C1 / H1:** rotate the production `SECRET_KEY`, the DB password and the `admin` password. Remove `backend/thimitech_backup.sql` from the repo and, optionally, purge `.env` from git history.
2. **L2:** choose how to handle CVs uploaded before this fix (move them, or block `/media/applications/` and use the admin).
3. **L3 / L4:** schedule the Pillow 13 upgrade, and run `npm audit fix` in `frontend/`.

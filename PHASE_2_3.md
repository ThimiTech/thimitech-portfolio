# Thimi Tech OS implementation notes

## Phase 2

Project management lives at `/app/projects` and `/api/pm/`. It is separate from public portfolio projects.

- Explicit project membership controls visibility. Project leads manage their own projects; HR/admin can manage all projects.
- Employees can move assigned tasks and comment on accessible project tasks.
- Projects start with a board containing Backlog, In progress, In review, and Done. Leads can add boards and columns.
- Tasks include priority, points, labels, assignee, dates, and milestone. Status follows the board column.
- Project hub stores milestones and HTTP(S) repository, documentation, video, and website links.
- Timeline uses task dates and milestones. Progress and organization totals respect project visibility.
- Archive preserves history. Reassign tasks before removing their assignees. Columns containing tasks cannot be deleted.

The public portfolio uses self-hosted Outfit and IBM Plex Mono, the existing warm paper palette, and a rust accent. The isolated Three.js terrain study uses GSAP ScrollTrigger for rotation and layer separation. It renders on demand, caps device pixel ratio, disposes GPU resources, and honors reduced motion. Project covers without uploaded images are abstract illustrations, not product screenshots.

## Phase 3 acceptance contract

User-confirmed payroll policy: monthly NPR, manual deductions. No automatic tax calculation, bank payment, or email transmission.

- Salary structures: one current structure per staff member; basic pay, allowances, manual deductions, effective date, active state.
- Payslips: generate monthly drafts from salary structures; retain copied amounts even when structures change; one employee per period; explicit draft, issued, paid, void lifecycle; issued monetary values cannot be edited.
- Expenses: record amount, currency, date, category, staff member, and description; draft/submitted/approved/rejected/paid lifecycle; finalized amounts are protected.
- Invoices: client, reference, dates, item quantities and rates, manual tax amount; totals use Decimal; draft/issued/paid/void lifecycle; no actual message or payment is sent.
- Finance totals are grouped by currency and exclude void records.
- Inventory: categories, uniquely tagged assets, purchase details, location, condition/status, assignment history and returns.
- Only available assets can be assigned; only active staff can receive assets; a database constraint and transaction prevent multiple active assignments; returns preserve history.
- Finance and inventory routes AND APIs require HR/admin. Employees and managers cannot access financial or inventory records.
- Apply migrations; run backend regression tests, frontend tests, type checking, production build, scoped lint, and browser acceptance checks.

## Local acceptance examples

Browser checks created clearly labeled examples in the local development database:

- `WALK` / Phase 2 walkthrough, with a dated task, comment, milestone, and project link.
- An inactive salary structure with a test-only note and a void payslip; not actual compensation.
- A void `TEST-ONLY-001` invoice and a rejected test-only expense; neither contributes to payable/outstanding totals.
- A retired `TEST-ONLY-001` asset under Acceptance examples, with a completed assignment/return history; not physical equipment.

These are development examples for review. No payment, invoice delivery, or email is performed by the new modules.

## Verification

Use Node 24 as required by the existing frontend engines field. `npm run test:unit -- --run`, `npm run type-check`, and `npm run build` cover the frontend; scoped ESLint covers new/edited components. For simultaneous backend test runs, use a distinct `DB_TEST_NAME` per process, as documented in CLAUDE.md.

Backend coverage includes membership isolation, cross-project validation, role restrictions, lifecycle locks, payroll uniqueness and snapshots, Decimal invoice rounding, currency separation, inactive staff rejection, and the database constraint preventing duplicate active asset assignments.

Final verification: 174 Django tests and 11 Vitest tests passed; production build, TypeScript, scoped ESLint, migration drift check, and OpenAPI validation passed. The production dependency audit reports zero vulnerabilities. The existing lint-tool dependency chain still has four development-only advisories; automatic remediation would downgrade the Vue ESLint configuration, so it was not forced. Three.js remains an isolated 180 KB gzip lazy chunk. OpenAPI has no errors; existing user-profile type-hint warnings and a generated status enum naming warning remain.

Browser acceptance covered 320/768/1024/1440 widths, portfolio gallery/detail navigation, scroll-linked terrain, login, project/task creation, task discussion and status changes, milestones, links, timeline, salary/payslip creation and issue/void, exact invoice totals, expense submission/rejection, and asset assignment/return history.

Three.js resource lifecycle follows [WebGLRenderer documentation](https://threejs.org/docs/pages/WebGLRenderer). Scroll binding and media cleanup use [ScrollTrigger](https://gsap.com/docs/v3/Plugins/ScrollTrigger/) and [gsap.matchMedia](https://gsap.com/docs/v3/GSAP/gsap.matchMedia/).

"""Import a work breakdown pasted from a spreadsheet (tab-separated, as Excel/Sheets copy it).

Columns: Module | Epic | Story | Task | Description | Status | Blocker | Assignee | Deadline.
A blank level cell inherits from the rows above, so a sheet laid out as an outline imports as a tree.
Items are matched by (parent, type, title): re-importing the same sheet updates details instead of duplicating.
"""
from datetime import datetime

from django.db import transaction

from .models import Column, Task

LEVELS = ['module', 'epic', 'story', 'task']
MAX_ROWS = 2000
STATUS_WORDS = [('done', ('done', 'complete', 'closed', 'finish', 'resolved')),
                ('review', ('review', 'qa', 'test', 'uat')),
                ('active', ('progress', 'doing', 'active', 'start', 'ongoing', 'wip', 'block'))]
DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%d %b %Y', '%d %B %Y', '%b %d, %Y', '%B %d, %Y']


def status_of(text):
    t = text.lower()
    if t in ('todo', 'to do', 'backlog', 'open', 'new', 'not started', 'pending'):
        return 'backlog'
    return next((status for status, words in STATUS_WORDS if any(w in t for w in words)), None)


def date_of(text):
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


@transaction.atomic
def import_sheet(project, text, actor):
    board = project.boards.order_by('id').first()
    columns = {}
    for c in board.columns.order_by('-position'):  # first column wins per status
        columns[c.status] = c
    backlog = columns.get(Column.Status.BACKLOG) or board.columns.order_by('position').first()
    people = {}
    for u in [*project.members.all(), project.lead]:
        if u.is_active and u.has_role('employee'):
            people[u.email.lower()] = people[(u.get_full_name() or u.email).lower()] = u
    existing = {(t.parent_id, t.type, t.title.lower()): t for t in Task.objects.filter(column__board__project=project)}
    path, created, updated, warnings = [None] * 4, set(), set(), []

    lines = text.splitlines()
    if len(lines) > MAX_ROWS:
        raise ValueError(f'Paste at most {MAX_ROWS} rows at a time.')
    for n, line in enumerate(lines, 1):
        cells = [c.strip() for c in line.split('\t')] + [''] * 9
        if not any(cells) or cells[0].lower() in ('module', 'modules'):  # blank or header row
            continue
        levels = [i for i in range(4) if cells[i]]
        if not levels:
            warnings.append(f'Row {n}: no module, epic, story or task title; skipped.')
            continue
        for i in levels:
            path[i + 1:] = [None] * (3 - i)
            parent = next((p for p in reversed(path[:i]) if p), None)
            key = (parent.pk if parent else None, LEVELS[i], cells[i][:200].lower())
            if key not in existing:
                existing[key] = Task.objects.create(title=cells[i][:200], type=LEVELS[i], parent=parent, column=backlog, created_by=actor)
                created.add(existing[key].pk)
            path[i] = existing[key]

        item, changed = path[levels[-1]], []
        description, status, blocker, assignee, deadline = cells[4:9]
        if description and description != item.description:
            item.description, changed = description, changed + ['description']
        if blocker and blocker != item.blocker:
            item.blocker, changed = blocker[:300], changed + ['blocker']
        if status:
            wanted = status_of(status)
            if wanted in columns and item.column_id != columns[wanted].pk:
                item.column, changed = columns[wanted], changed + ['column']
            elif not wanted:
                warnings.append(f'Row {n}: status "{status}" not recognised; left as is.')
            if 'block' in status.lower() and not item.blocker:
                item.blocker, changed = 'Blocked', changed + ['blocker']
        if assignee:
            user = people.get(assignee.lower())
            if not user:
                warnings.append(f'Row {n}: "{assignee}" is not a project member; left unassigned.')
            elif user.pk != item.assignee_id:
                item.assignee, changed = user, changed + ['assignee']
        if deadline:
            due = date_of(deadline)
            if not due:
                warnings.append(f'Row {n}: deadline "{deadline}" is not a date (use YYYY-MM-DD).')
            elif due != item.due_date:
                item.due_date, changed = due, changed + ['due_date']
        if changed:
            item.save(update_fields=changed)
            updated.add(item.pk)
    return {'created': len(created), 'updated': len(updated - created), 'warnings': warnings}

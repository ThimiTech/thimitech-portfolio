"""Issue history: which fields of a task changed, by whom, stored as display text (see `TaskActivity`)."""
from django.db.models import Max

from .models import Task, TaskActivity

TRACKED = ('title', 'type', 'column', 'assignee', 'priority', 'estimate', 'parent', 'sprint', 'milestone',
           'start_date', 'due_date', 'blocker', 'labels', 'blocked_by', 'description')
QUIET = {'description'}  # too long to quote; the history says "updated the description"


def key_of(task):
    return f'{task.column.board.project.key}-{task.pk}'


def display(task, field):
    if field == 'blocked_by':
        return ', '.join(sorted(key_of(t) for t in task.blocked_by.select_related('column__board__project'))) if task.pk else ''
    value = getattr(task, field)
    if value in (None, '', []):
        return ''
    if field == 'column':
        return value.name
    if field == 'assignee':
        return value.get_full_name() or value.email
    if field == 'parent':
        return f'{key_of(value)} {value.title}'
    if field == 'sprint':
        return value.name
    if field == 'milestone':
        return value.title
    if field == 'labels':
        return ', '.join(value)
    if field in ('type', 'priority'):
        return getattr(task, f'get_{field}_display')()
    if field in ('start_date', 'due_date'):
        return value.isoformat()
    return str(value)


def snapshot(task):
    return {f: display(task, f) for f in TRACKED}


def record(task, before, actor):
    """Write one row per field that differs from `before` (a `snapshot` taken before the save)."""
    after = snapshot(task)
    rows = [TaskActivity(task=task, actor=actor, field=f, old='' if f in QUIET else before[f][:300],
                         new='' if f in QUIET else after[f][:300])
            for f in TRACKED if before[f] != after[f]]
    TaskActivity.objects.bulk_create(rows)
    return rows


def created(task, actor):
    TaskActivity.objects.create(task=task, actor=actor, field='created', new=task.get_type_display())


def next_position(project):
    """New items go to the bottom of the backlog, as in Jira."""
    top = Task.objects.filter(column__board__project=project).aggregate(m=Max('position'))['m']
    return 0 if top is None else top + 10


def rerank(project, ids):
    """Put `ids` in this order without disturbing anything else.

    Every view (a board column, a sprint, the backlog, an epic) shows a subset of one project-wide rank. The subset's
    rank slots are redistributed in the new order, so items outside it keep their places. Duplicate slots (older data
    all sat at 0) are first spread out to distinct values. Uses bulk_update: ranking is not audited or recorded.
    """
    rows = list(Task.objects.filter(column__board__project=project).order_by('position', 'id').only('id', 'position'))
    by_id = {t.pk: t for t in rows}
    original = {t.pk: t.position for t in rows}
    if any(i not in by_id for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Reorder only items of this project, each once.')
    if len({t.position for t in rows}) != len(rows):
        for index, t in enumerate(rows):
            t.position = index * 10
    slots = sorted(by_id[i].position for i in ids)
    for i, slot in zip(ids, slots):
        by_id[i].position = slot
    Task.objects.bulk_update([t for t in rows if t.position != original[t.pk]], ['position'], batch_size=500)

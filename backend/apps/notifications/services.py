"""push() is the one entry point modules use to drop items into people's in-app inboxes."""
from .models import Notification


def push(users, kind, title, body='', link='', exclude=None):
    """Create one notification per distinct active user (None and `exclude` are skipped). Runs inside the caller's
    transaction, so a rolled-back action leaves no orphan notifications."""
    seen, rows = set(), []
    for u in users:
        if u is None or not u.is_active or u.pk in seen or (exclude is not None and u.pk == exclude.pk):
            continue
        seen.add(u.pk)
        rows.append(Notification(recipient=u, kind=kind, title=title[:200], body=body, link=link))
    Notification.objects.bulk_create(rows)
    return len(rows)

import datetime

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from .models import Notice


@shared_task
def email_due_urgent_notices():
    """Email urgent notices that have gone live but were never emailed (scheduled ones, or notices
    edited to urgent). Only looks back one day so a long-stopped beat doesn't mail stale news."""
    now = timezone.now()
    due = Notice.objects.filter(
        category=Notice.Category.URGENT, emailed_at__isnull=True,
        publish_at__lte=now, publish_at__gte=now - datetime.timedelta(days=1),
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    from .views import email_urgent  # views imports DRF; keep worker import light until needed
    sent = [n.pk for n in due if email_urgent(n)]
    return {'emailed': sent}

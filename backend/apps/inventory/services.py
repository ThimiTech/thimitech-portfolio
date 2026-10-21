from django.db.models import Count, Q
from django.utils import timezone
from .models import Asset, Assignment


def summary_payload():
    counts = Asset.objects.aggregate(total=Count('id'), available=Count('id', filter=Q(status='available')), assigned=Count('id', filter=Q(status='assigned')), maintenance=Count('id', filter=Q(status='maintenance')), retired=Count('id', filter=Q(status='retired')))
    counts['overdue'] = Assignment.objects.filter(returned_at__isnull=True, due_back__lt=timezone.localdate()).count()
    return counts

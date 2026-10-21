"""Working-day maths shared by leave and attendance."""
import datetime

from apps.org.models import Organization
from .models import Holiday


def holiday_dates(start, end):
    return set(
        Holiday.objects.filter(date__range=(start, end), is_optional=False).values_list('date', flat=True)
    )


def working_days(start, end, *, org=None):
    """Dates in [start, end] that are neither weekend (per Organization policy) nor a mandatory holiday."""
    if end < start:
        return []
    weekend = set((org or Organization.load()).weekend_days)
    holidays = holiday_dates(start, end)
    days, d = [], start
    while d <= end:
        if d.weekday() not in weekend and d not in holidays:
            days.append(d)
        d += datetime.timedelta(days=1)
    return days


def is_working_day(day):
    return bool(working_days(day, day))

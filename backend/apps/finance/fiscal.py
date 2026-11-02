"""Nepal fiscal year (Shrawan 1 to Ashadh end) and Bikram Sambat dates, derived from AD dates."""
import re
from datetime import date, timedelta

import nepali_datetime as nd
from django.utils import timezone

BS_MONTHS = ['Baishakh', 'Jestha', 'Asar', 'Shrawan', 'Bhadra', 'Asoj', 'Kartik', 'Mangsir', 'Poush', 'Magh', 'Falgun', 'Chaitra']
FY_RE = re.compile(r'^(\d{4})/(\d{2})$')


def bs(d: date) -> nd.date:
    return nd.date.from_datetime_date(d)


def bs_str(d: date | None) -> str:
    if not d:
        return ''
    b = bs(d)
    return f'{b.year:04d}-{b.month:02d}-{b.day:02d}'


def bs_label(d: date) -> str:
    b = bs(d)
    return f'{b.day} {BS_MONTHS[b.month - 1]} {b.year}'


def fy_of(d: date) -> str:
    b = bs(d)
    start = b.year if b.month >= 4 else b.year - 1
    return f'{start}/{(start + 1) % 100:02d}'


def current_fy() -> str:
    return fy_of(timezone.localdate())


def parse_fy(name: str) -> int:
    m = FY_RE.match(name or '')
    if not m or (int(m[1]) + 1) % 100 != int(m[2]):
        raise ValueError('Use a fiscal year like 2082/83.')
    return int(m[1])


def fy_range(name: str) -> tuple[date, date]:
    y = parse_fy(name)
    return nd.date(y, 4, 1).to_datetime_date(), nd.date(y + 1, 4, 1).to_datetime_date() - timedelta(days=1)


def fy_months(name: str) -> list[dict]:
    """The 12 BS months of a fiscal year, Shrawan first, with their AD start/end dates."""
    y = parse_fy(name)
    starts = [(y, m) for m in range(4, 13)] + [(y + 1, m) for m in range(1, 5)]
    out = []
    for (by, bm), (ny, nm) in zip(starts, starts[1:]):
        out.append({'label': f'{BS_MONTHS[bm - 1]} {by}', 'start': nd.date(by, bm, 1).to_datetime_date(),
                    'end': nd.date(ny, nm, 1).to_datetime_date() - timedelta(days=1)})
    return out


def next_bs_month_day(d: date, day: int) -> date:
    """AD date of `day` in the BS month after the one containing `d` (statutory deadlines: TDS 25th, SSF 15th)."""
    b = bs(d)
    y, m = (b.year + 1, 1) if b.month == 12 else (b.year, b.month + 1)
    return nd.date(y, m, day).to_datetime_date()


def recent_fys(earliest: date | None, count_min: int = 3) -> list[str]:
    """Fiscal years from `earliest` (or the last few) up to the current one, newest first."""
    today = timezone.localdate()
    start = parse_fy(fy_of(min(earliest or today, today)))
    end = parse_fy(fy_of(today))
    start = min(start, end - count_min + 1)
    return [f'{y}/{(y + 1) % 100:02d}' for y in range(end, start - 1, -1)]

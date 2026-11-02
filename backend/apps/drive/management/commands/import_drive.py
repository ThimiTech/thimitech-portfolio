"""Copy a folder from disk into the drive, keeping its subfolders.

  manage.py import_drive "E:/docs/salary logs" --space finance --into "Payroll/Salary transfer slips" --match-employees

Fiscal years are read from names like "81-82", "81.82" or "82_83", or from 13-digit millisecond timestamps
(e-banking exports: transfer_1775224729881.pdf). Re-running skips files already there (same folder + name + size)."""
import os
import re
from datetime import datetime, timezone as tz

from django.core.files import File as DjFile
from django.core.management.base import BaseCommand, CommandError

from apps.drive.access import ensure_path
from apps.drive.models import File, Space
from apps.finance.fiscal import fy_of
from apps.users.models import User

FY_NAME = re.compile(r'(?<!\d)(8\d)[\s._-](8\d)(?!\d)')
EPOCH_MS = re.compile(r'(?<!\d)(1[6-9]\d{11})(?!\d)')
SKIP = re.compile(r'^(~\$|\.|thumbs\.db$|desktop\.ini$)', re.I)


def fiscal_year(name):
    m = FY_NAME.search(name)
    if m and int(m[2]) == int(m[1]) + 1:
        return f'20{m[1]}/{m[2]}'
    m = EPOCH_MS.search(name)
    if m:
        return fy_of(datetime.fromtimestamp(int(m[1]) / 1000, tz=tz.utc).date())
    return ''


def employee_matcher():
    """First-name prefix match ('johnn' in 'johnny-june.pdf' -> Johnny) against active staff."""
    people = [(u, re.sub(r'[^a-z]', '', (u.first_name or '').lower())) for u in User.objects.filter(is_active=True).exclude(role='guest')]

    def match(text):
        words = re.findall(r'[a-z]+', text.lower())
        hits = {u for u, first in people if len(first) >= 4 and any(w[:5] == first[:5] and len(w) >= 4 for w in words)}
        return hits.pop() if len(hits) == 1 else None
    return match


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('source')
        parser.add_argument('--space', choices=Space.values, required=True)
        parser.add_argument('--into', default='', help='Folder path in the space, e.g. "Audit/FY 2081-82".')
        parser.add_argument('--fy', default='', help='Fiscal year for every file (otherwise detected per file).')
        parser.add_argument('--folder-fy', default='', help='Tag the target folder with this fiscal year.')
        parser.add_argument('--employee', type=int, help='Link every file to this user id.')
        parser.add_argument('--match-employees', action='store_true', help='Link files whose name contains a staff first name.')
        parser.add_argument('--files', nargs='*', help='Only these file names from the source folder (no recursion).')

    def handle(self, source, space, into, fy, folder_fy, employee, match_employees, files, **_):
        if not os.path.isdir(source):
            raise CommandError(f'Not a folder: {source}')
        target = ensure_path(space, into.split('/'), fiscal_year=folder_fy) if into else None
        match = employee_matcher() if match_employees else None
        fixed = User.objects.get(pk=employee) if employee else None
        added = skipped = 0
        for root, dirs, names in os.walk(source):
            dirs[:] = [] if files else sorted(d for d in dirs if not SKIP.match(d))
            rel = os.path.relpath(root, source)
            folder = ensure_path(space, [] if rel == '.' else rel.replace('\\', '/').split('/'), parent=target)
            for name in sorted(names):
                if SKIP.match(name) or (files and name not in files):
                    continue
                path = os.path.join(root, name)
                size = os.path.getsize(path)
                if File.objects.filter(space=space, folder=folder, name=name, size=size).exists():
                    skipped += 1
                    continue
                who = fixed or (match(f'{rel} {name}') if match else None)
                with open(path, 'rb') as fh:
                    f = File(space=space, folder=folder, name=name, size=size, employee=who,
                             fiscal_year=fy or fiscal_year(name))
                    f.file.save(name, DjFile(fh), save=True)
                added += 1
                self.stdout.write(f"  + {'/'.join(folder.path() if folder else [])}/{name}  fy={f.fiscal_year or '-'}  "
                                  f"employee={who.get_full_name() if who else '-'}")
        self.stdout.write(self.style.SUCCESS(f'{added} added, {skipped} already there'))

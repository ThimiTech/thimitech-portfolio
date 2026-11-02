"""Load a private books bundle (zip or folder) into this database: bank ledger, payroll history, staff claims,
dollar card, statements and the document drive. Safe to re-run: every step skips what is already there.

  manage.py load_books_bundle /srv/private/thimitech-books-bundle.zip

The bundle holds real financial data, so it is never committed: copy it to the server (scp), load it, delete it.
manifest.json at its root:
  {"books": {...import_books options; file options are paths inside the bundle...},
   "drive": [{"dir": "drive/01", "space": "finance", "into": "Audit/FY 2081-82", "folder_fy": "2081/82",
              "fy": "", "match_employees": false, "employee": "Full Name"}, ...]}
A super admin must exist first (imported rows record who created them)."""
import json
import os
import tempfile
import zipfile

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.users.models import User

BOOK_FILES = ('ledger', 'statement_images', 'salary_xlsx', 'expense_xlsx')
BOOK_JSON = ('claimants', 'ledger_categories')


def safe_extract(zip_path, dest):
    with zipfile.ZipFile(zip_path) as zf:
        root = os.path.realpath(dest)
        for member in zf.namelist():
            target = os.path.realpath(os.path.join(dest, member))
            if not target.startswith(root + os.sep) and target != root:
                raise CommandError(f'Unsafe path in bundle: {member}')
        zf.extractall(dest)


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('bundle', help='Path to the bundle .zip or an unpacked bundle folder.')

    def handle(self, bundle, **_):
        if not User.objects.filter(role='super_admin').exists():
            raise CommandError('Create a super admin first (manage.py createsuperuser).')
        if os.path.isdir(bundle):
            return self.load(bundle)
        if not zipfile.is_zipfile(bundle):
            raise CommandError(f'Not a folder or zip: {bundle}')
        with tempfile.TemporaryDirectory() as tmp:
            safe_extract(bundle, tmp)
            self.load(tmp)

    def load(self, root):
        path = os.path.join(root, 'manifest.json')
        if not os.path.exists(path):
            raise CommandError('manifest.json not found at the bundle root.')
        with open(path, encoding='utf-8') as fh:
            manifest = json.load(fh)
        books = dict(manifest.get('books', {}))
        for key in BOOK_FILES:
            if books.get(key):
                books[key] = os.path.join(root, books[key])
        for key in BOOK_JSON:
            if key in books:
                books[key] = json.dumps(books[key])
        if books:
            self.stdout.write(self.style.MIGRATE_HEADING('Books'))
            call_command('import_books', stdout=self.stdout, **books)
        for entry in manifest.get('drive', []):
            self.stdout.write(self.style.MIGRATE_HEADING(f"Drive: {entry['space']} / {entry.get('into', '')}"))
            employee = None
            if entry.get('employee'):
                first, _, last = entry['employee'].partition(' ')
                person = User.objects.filter(first_name__iexact=first, last_name__iexact=last).first()
                if not person:
                    raise CommandError(f"No staff named {entry['employee']} (import the books with create_staff first).")
                employee = person.pk
            call_command('import_drive', os.path.join(root, entry['dir']), space=entry['space'], into=entry.get('into', ''),
                         fy=entry.get('fy', ''), folder_fy=entry.get('folder_fy', ''), employee=employee,
                         match_employees=entry.get('match_employees', False), stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS('Bundle loaded.'))

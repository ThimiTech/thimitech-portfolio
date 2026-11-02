"""Who can see and change what in the drive. Access is per space; an employee can also always read files linked to them."""
from django.db.models import Q

from .models import File, Folder, Space


def readable_spaces(user):
    spaces = []
    if user.has_role('employee'):
        spaces.append(Space.COMPANY)
    if user.can_finance():
        spaces.append(Space.FINANCE)
    if user.has_role('hr_admin'):
        spaces.append(Space.PEOPLE)
    return spaces


def can_write(user, space):
    return {Space.COMPANY: user.has_role('employee'), Space.FINANCE: user.can_finance(),
            Space.PEOPLE: user.has_role('hr_admin')}.get(space, False)


def can_delete(user, obj):
    """Company drive: the uploader or HR. Finance and people files: anyone who can write there."""
    if not can_write(user, obj.space):
        return False
    owner = getattr(obj, 'uploaded_by_id', None) or getattr(obj, 'created_by_id', None)
    return obj.space != Space.COMPANY or owner == user.pk or user.has_role('hr_admin')


def can_share(user, space):
    """External share links: finance roles and HR only, and only for spaces they can write."""
    return can_write(user, space) and (user.can_finance() or user.has_role('hr_admin'))


def can_link_records(user):
    """Linking a document to someone else, or to a finance record, decides who else can read it."""
    return user.can_finance() or user.has_role('hr_admin')


def files_for(user):
    return File.objects.filter(Q(space__in=readable_spaces(user)) | Q(employee=user))


def folders_for(user):
    return Folder.objects.filter(space__in=readable_spaces(user))


def ensure_path(space, names, user=None, fiscal_year='', parent=None):
    """Get or create the folder chain `names` under `parent` in `space` (case-insensitive); returns the last folder."""
    for name in [n.strip() for n in names if n and n.strip()]:
        found = Folder.objects.filter(space=space, parent=parent, name__iexact=name[:120]).first()
        parent = found or Folder.objects.create(space=space, parent=parent, name=name[:120], created_by=user)
    if parent and fiscal_year and not parent.fiscal_year:
        parent.fiscal_year = fiscal_year
        parent.save(update_fields=['fiscal_year'])
    return parent

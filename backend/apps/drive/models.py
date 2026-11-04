import os
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.users.models import classification_field


def drive_path(instance, filename):
    # Unguessable dir; files are served only through the scoped API (/api/drive/files/{id}/content/).
    return f'drive/{uuid.uuid4().hex}/{os.path.basename(filename)}'


class Space(models.TextChoices):
    COMPANY = 'company', 'Company drive'   # everyone: letterheads, logos, templates, email signatures
    FINANCE = 'finance', 'Finance'         # finance roles: statements, payroll logs, SSF, tax, audit
    PEOPLE = 'people', 'People files'      # HR: offer/experience letters, contracts


class Folder(models.Model):
    space = models.CharField(max_length=8, choices=Space.choices)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    name = models.CharField(max_length=120)
    fiscal_year = models.CharField(max_length=7, blank=True, help_text='e.g. 2081/82 for an audit folder.')
    # A floor for everything inside: subfolders and files are never classified below their folder.
    classification = classification_field()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [Lower('name')]
        constraints = [
            models.UniqueConstraint(Lower('name'), 'space', 'parent', name='unique_folder_name'),
            models.UniqueConstraint(Lower('name'), 'space', condition=models.Q(parent__isnull=True), name='unique_root_folder_name'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.parent_id:  # read from the DB: a cached parent may predate a reclassification
            self.classification = max(self.classification, Folder.objects.get(pk=self.parent_id).classification)
        adding = self._state.adding
        super().save(*args, **kwargs)
        if not adding:  # raised, or moved under a stricter parent: lift the contents (never lowers them)
            ids = self.descendant_ids()
            Folder.objects.filter(pk__in=ids, classification__lt=self.classification).update(classification=self.classification)
            File.objects.filter(folder_id__in=ids, classification__lt=self.classification).update(classification=self.classification)

    def path(self):
        names, node = [], self
        while node:
            names.append(node.name)
            node = node.parent
        return names[::-1]

    def descendant_ids(self):
        ids, frontier = [self.pk], [self.pk]
        while frontier:
            frontier = list(Folder.objects.filter(parent_id__in=frontier).values_list('pk', flat=True))
            ids += frontier
        return ids


class File(models.Model):
    space = models.CharField(max_length=8, choices=Space.choices)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.PROTECT, related_name='files')
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=drive_path, max_length=300)
    size = models.PositiveIntegerField(default=0, editable=False)
    description = models.TextField(blank=True)
    fiscal_year = models.CharField(max_length=7, blank=True)
    classification = classification_field()
    # What the document is about: these drive the "linked documents" on people, projects and finance records,
    # and an employee can always read files linked to them (their payslip transfers, offer letter, receipts).
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='drive_files')
    project = models.ForeignKey('pm.Project', null=True, blank=True, on_delete=models.SET_NULL, related_name='drive_files')
    transaction = models.ForeignKey('finance.Transaction', null=True, blank=True, on_delete=models.SET_NULL, related_name='files')
    expense = models.ForeignKey('finance.Expense', null=True, blank=True, on_delete=models.SET_NULL, related_name='files')
    invoice = models.ForeignKey('finance.Invoice', null=True, blank=True, on_delete=models.SET_NULL, related_name='files')
    statement = models.ForeignKey('finance.Statement', null=True, blank=True, on_delete=models.SET_NULL, related_name='files')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [Lower('name'), 'id']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.folder_id:  # read from the DB: a cached folder may predate a reclassification
            self.classification = max(self.classification, Folder.objects.get(pk=self.folder_id).classification)
        super().save(*args, **kwargs)

    @property
    def extension(self):
        # From the stored file, not the (renamable) display name: it decides how the file is served.
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')

    @property
    def download_name(self):
        ext = os.path.splitext(self.file.name)[1]
        return self.name if self.name.lower().endswith(ext.lower()) else self.name + ext


def new_token():
    return secrets.token_urlsafe(24)


class ShareLink(models.Model):
    """Read-only, expiring link to one folder (with subfolders) or one file, for people without an account (e.g. the CA)."""
    token = models.CharField(max_length=40, unique=True, default=new_token, editable=False)
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE, related_name='share_links')
    file = models.ForeignKey(File, null=True, blank=True, on_delete=models.CASCADE, related_name='share_links')
    label = models.CharField(max_length=120, blank=True, help_text='Who it is for, e.g. "CA - FY 2081/82 audit".')
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(
            condition=models.Q(folder__isnull=False, file__isnull=True) | models.Q(folder__isnull=True, file__isnull=False),
            name='share_one_target')]

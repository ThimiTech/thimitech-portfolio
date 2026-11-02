import os

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.finance.fiscal import parse_fy
from .access import can_link_records, can_write, ensure_path, folders_for
from .models import File, Folder, ShareLink, Space

MAX_FILE_BYTES = getattr(settings, 'DRIVE_MAX_FILE_BYTES', 25 * 1024 * 1024)
LINK_FIELDS = ['transaction', 'expense', 'invoice', 'statement']


def name_of(user):
    return (user.get_full_name() or user.email) if user else ''


def check_fy(value):
    if value:
        try:
            parse_fy(value)
        except ValueError as e:
            raise serializers.ValidationError(str(e))
    return value


class FolderSerializer(serializers.ModelSerializer):
    path = serializers.SerializerMethodField()
    file_count = serializers.IntegerField(read_only=True, required=False)
    folder_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Folder
        fields = ['id', 'space', 'parent', 'name', 'fiscal_year', 'path', 'file_count', 'folder_count', 'created_at']
        read_only_fields = ['created_at']

    def get_path(self, folder) -> list[dict]:
        out, node = [], folder
        while node:
            out.append({'id': node.pk, 'name': node.name})
            node = node.parent
        return out[::-1]

    def validate_fiscal_year(self, value):
        return check_fy(value)

    def validate(self, attrs):
        user = self.context['request'].user
        space = attrs.get('space', getattr(self.instance, 'space', None))
        parent = attrs.get('parent', getattr(self.instance, 'parent', None))
        if self.instance and 'space' in attrs and attrs['space'] != self.instance.space:
            raise serializers.ValidationError({'space': 'Move the files instead; folders stay in their space.'})
        if parent:
            if not folders_for(user).filter(pk=parent.pk).exists() or parent.space != space:
                raise serializers.ValidationError({'parent': 'Choose a folder in the same space.'})
            if self.instance and parent.pk in self.instance.descendant_ids():
                raise serializers.ValidationError({'parent': 'A folder cannot move inside itself.'})
        if not can_write(user, space):
            raise serializers.ValidationError({'space': 'You cannot add folders here.'})
        name = attrs.get('name', getattr(self.instance, 'name', '')).strip()
        if not name or name in ('.', '..') or '/' in name or '\\' in name:
            raise serializers.ValidationError({'name': 'Use a folder name without slashes.'})
        clash = Folder.objects.filter(space=space, parent=parent, name__iexact=name)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({'name': 'A folder with this name already exists here.'})
        attrs['name'] = name
        return attrs


class FileSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=True)
    relative_path = serializers.CharField(write_only=True, required=False, allow_blank=True,
                                          help_text='Folder upload: path inside the chosen folder, e.g. "salary logs/june.pdf".')
    extension = serializers.CharField(read_only=True)
    url = serializers.SerializerMethodField()
    title = serializers.CharField(source='name', read_only=True)
    folder_name = serializers.CharField(source='folder.name', read_only=True, default='')
    uploaded_by_name = serializers.SerializerMethodField()
    employee_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True, default='')
    transaction_label = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = ['id', 'space', 'folder', 'folder_name', 'name', 'title', 'extension', 'size', 'description', 'fiscal_year',
                  'employee', 'employee_name', 'project', 'project_name', 'transaction', 'transaction_label', 'expense',
                  'invoice', 'statement', 'uploaded_by_name', 'created_at', 'updated_at', 'url', 'file', 'relative_path']
        read_only_fields = ['size', 'created_at', 'updated_at']
        extra_kwargs = {'name': {'required': False}, 'space': {'required': False}}

    def get_url(self, f) -> str:
        return f'/api/drive/files/{f.pk}/content/'

    def get_uploaded_by_name(self, f) -> str:
        return name_of(f.uploaded_by)

    def get_employee_name(self, f) -> str:
        return name_of(f.employee)

    def get_transaction_label(self, f) -> str:
        t = f.transaction
        return f'{t.date:%d %b %Y} · {t.description[:60]} · {t.credit or t.debit}' if t else ''

    def validate_file(self, f):
        if f.size > MAX_FILE_BYTES:
            raise serializers.ValidationError(f'Files must be {MAX_FILE_BYTES // 1048576} MB or smaller.')
        return f

    def validate_fiscal_year(self, value):
        return check_fy(value)

    def validate(self, attrs):
        user = self.context['request'].user
        if self.instance and 'file' in attrs:
            raise serializers.ValidationError({'file': 'Upload a new file instead of replacing this one.'})
        folder = attrs.get('folder', getattr(self.instance, 'folder', None))
        if folder and not folders_for(user).filter(pk=folder.pk).exists():
            raise serializers.ValidationError({'folder': 'Folder not found.'})
        space = folder.space if folder else attrs.get('space', getattr(self.instance, 'space', None))
        if space not in Space.values:
            raise serializers.ValidationError({'space': 'Choose a space or a folder.'})
        claim = attrs.get('expense')
        own_receipt = (not self.instance and claim and claim.employee_id == user.pk and claim.status in ('draft', 'rejected')
                       and not folder and space == Space.FINANCE and not any(attrs.get(k) for k in ('transaction', 'invoice', 'statement')))
        if own_receipt:  # an employee attaching a receipt to their own claim; it lands in Finance, linked to them
            attrs['employee'] = user
        elif not can_write(user, space) or (self.instance and not can_write(user, self.instance.space)):
            raise serializers.ValidationError({'space': 'You cannot add or move files here.'})
        attrs['space'] = space
        if not can_link_records(user) and not own_receipt:
            if attrs.get('employee') not in (None, user):
                raise serializers.ValidationError({'employee': 'You can only link documents to yourself.'})
            if any(attrs.get(k) for k in LINK_FIELDS):
                raise serializers.ValidationError('Only finance staff can link documents to finance records.')
        rel = attrs.pop('relative_path', '').replace('\\', '/').strip('/')
        if rel and not self.instance:
            parts = [p for p in rel.split('/') if p not in ('', '.', '..')]
            attrs['folder'] = ensure_path(space, parts[:-1], user, parent=folder)
        if own_receipt:
            attrs['folder'] = ensure_path(space, ['Receipts & claims', user.get_full_name() or user.email], user)
        if 'file' in attrs and not attrs.get('name'):
            attrs['name'] = os.path.basename(attrs['file'].name)[:255]
        if 'name' in attrs:
            attrs['name'] = attrs['name'].strip()[:255] or 'untitled'
        return attrs

    def create(self, validated_data):
        validated_data['size'] = validated_data['file'].size
        return super().create(validated_data)


class ShareLinkSerializer(serializers.ModelSerializer):
    target_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()
    days = serializers.IntegerField(write_only=True, min_value=1, max_value=90, default=14)

    class Meta:
        model = ShareLink
        fields = ['id', 'token', 'folder', 'file', 'label', 'expires_at', 'revoked_at', 'created_by_name', 'created_at',
                  'target_name', 'active', 'days']
        read_only_fields = ['token', 'expires_at', 'revoked_at', 'created_at']

    def get_target_name(self, link) -> str:
        return link.folder.name if link.folder else link.file.name

    def get_created_by_name(self, link) -> str:
        return name_of(link.created_by)

    def get_active(self, link) -> bool:
        return not link.revoked_at and link.expires_at > timezone.now()

    def validate(self, attrs):
        if bool(attrs.get('folder')) == bool(attrs.get('file')):
            raise serializers.ValidationError('Share either a folder or a file.')
        attrs['expires_at'] = timezone.now() + timezone.timedelta(days=attrs.pop('days', 14))
        return attrs

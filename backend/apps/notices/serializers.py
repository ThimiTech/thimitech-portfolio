import os

from django.core.validators import FileExtensionValidator
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import empty

from apps.org.models import Department

from .models import Notice

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'docx', 'xlsx']
STAFF_ROLES = ['employee', 'manager', 'hr_admin', 'super_admin']

# NoticeRead rows whose reader is in the notice's audience (mirrors views.audience_users).
AUDIENCE_READS = Q(user__is_active=True, user__role__in=STAFF_ROLES) & (
    Q(notice__audience=Notice.Audience.ALL) | Q(user__profile__department_id=F('notice__department_id'))
)


def notice_status(notice, now=None):
    now = now or timezone.now()
    if notice.publish_at > now:
        return 'scheduled'
    if notice.expires_at and notice.expires_at <= now:
        return 'expired'
    return 'published'


def user_brief(user, request):
    """{id, full_name, photo} — photo is an absolute URL or null (guests have no profile)."""
    if user is None:
        return None
    profile = getattr(user, 'profile', None)
    photo = None
    if profile and profile.photo:
        photo = request.build_absolute_uri(profile.photo.url) if request else profile.photo.url
    return {'id': user.id, 'full_name': user.full_name, 'photo': photo}


class OptionalBooleanField(serializers.BooleanField):
    # DRF treats an omitted checkbox in multipart as False on PUT; omitted must mean "unchanged".
    default_empty_html = empty


class NoticeSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()
    department_id = serializers.PrimaryKeyRelatedField(
        source='department', queryset=Department.objects.all(),
        write_only=True, required=False, allow_null=True,
    )
    author = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    pinned = OptionalBooleanField(required=False)
    attachment = serializers.FileField(
        required=False, allow_null=True,
        validators=[FileExtensionValidator(ALLOWED_EXTENSIONS)],
    )
    attachment_name = serializers.SerializerMethodField()
    remove_attachment = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Notice
        fields = [
            'id', 'title', 'body', 'category', 'audience', 'department', 'department_id',
            'pinned', 'publish_at', 'expires_at', 'attachment', 'attachment_name',
            'remove_attachment', 'author', 'status', 'is_read', 'read_count', 'can_edit',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {'publish_at': {'required': False}}

    # ---- read side -------------------------------------------------------
    def _user(self):
        return self.context['request'].user

    def get_department(self, obj) -> dict | None:
        d = obj.department
        return {'id': d.id, 'name': d.name} if d else None

    def get_author(self, obj) -> dict | None:
        return user_brief(obj.author, self.context.get('request'))

    def get_status(self, obj) -> str:
        return notice_status(obj)

    def get_is_read(self, obj) -> bool:
        if hasattr(obj, 'is_read'):
            return obj.is_read
        return obj.reads.filter(user=self._user()).exists()

    def _can_manage(self, obj):
        user = self._user()
        return user.has_role('hr_admin') or obj.author_id == user.id

    def get_read_count(self, obj) -> int | None:
        if not self._can_manage(obj):
            return None
        return obj.read_count if hasattr(obj, 'read_count') else obj.reads.filter(AUDIENCE_READS).count()

    def get_can_edit(self, obj) -> bool:
        return self._can_manage(obj)

    def get_attachment_name(self, obj) -> str | None:
        return os.path.basename(obj.attachment.name) if obj.attachment else None

    def to_representation(self, obj):
        data = super().to_representation(obj)
        # never expose the raw /media path: files are served through the scoped API action
        url = None
        if obj.attachment:
            url = reverse('notice-attachment', args=[obj.pk])
            request = self.context.get('request')
            url = request.build_absolute_uri(url) if request else url
        data['attachment'] = url
        return data

    # ---- write side ------------------------------------------------------
    def validate_attachment(self, f):
        if f and f.size > MAX_ATTACHMENT_BYTES:
            raise serializers.ValidationError('Attachment must be 10 MB or smaller.')
        return f

    def validate(self, attrs):
        user = self._user()
        inst = self.instance

        def current(key, default=None):
            return attrs[key] if key in attrs else getattr(inst, key, default)

        audience = current('audience', Notice.Audience.ALL)
        department = current('department')
        if audience == Notice.Audience.ALL:
            attrs['department'] = None
        elif department is None:
            raise serializers.ValidationError(
                {'department_id': 'Choose a department for a department notice.'})

        is_hr = user.has_role('hr_admin')
        if not is_hr:
            if audience != Notice.Audience.DEPARTMENT:
                raise serializers.ValidationError(
                    {'audience': 'Only HR admins can post to everyone; managers post to their own department.'})
            if department.manager_id != user.id:
                raise serializers.ValidationError(
                    {'department_id': 'You can only post notices to departments you manage.'})
            if 'pinned' in attrs and attrs['pinned'] != (inst.pinned if inst else False):
                raise serializers.ValidationError({'pinned': 'Only HR admins can pin or unpin notices.'})

        publish_at = current('publish_at') or timezone.now()
        expires_at = current('expires_at')
        if expires_at and expires_at <= publish_at:
            raise serializers.ValidationError({'expires_at': 'Expiry must be after the publish time.'})
        return attrs

    def _apply_attachment_removal(self, validated_data):
        if validated_data.pop('remove_attachment', False) and 'attachment' not in validated_data:
            validated_data['attachment'] = None

    def create(self, validated_data):
        self._apply_attachment_removal(validated_data)
        if validated_data.get('attachment') is None:
            validated_data.pop('attachment', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._apply_attachment_removal(validated_data)
        if 'attachment' in validated_data:
            if instance.attachment:  # removed or replaced: don't orphan the old file
                instance.attachment.delete(save=False)
            if validated_data['attachment'] is None:
                validated_data['attachment'] = ''
        return super().update(instance, validated_data)


class ReaderSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField()
    photo = serializers.CharField(allow_null=True)
    department = serializers.DictField(allow_null=True)
    read_at = serializers.DateTimeField(allow_null=True)


class ReadersResponseSerializer(serializers.Serializer):
    audience_count = serializers.IntegerField()
    read_count = serializers.IntegerField()
    read = ReaderSerializer(many=True)
    unread = ReaderSerializer(many=True)

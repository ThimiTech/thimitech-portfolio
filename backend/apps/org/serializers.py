from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_image_file_extension
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import Department, EmployeeProfile, Organization

User = get_user_model()

MAX_PHOTO_BYTES = 3 * 1024 * 1024
WORK_POLICY_FIELDS = ('work_start', 'work_end', 'late_grace_minutes', 'weekend_days')

# People: which fields each audience may see / write.
DIRECTORY_FIELDS = (
    'id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'is_active',
    'designation', 'department', 'manager', 'photo', 'phone', 'join_date', 'skills', 'bio',
)
SENSITIVE_FIELDS = (
    'employee_code', 'employment_type', 'date_of_birth', 'address',
    'emergency_contact_name', 'emergency_contact_phone',
)
SELF_EDITABLE = {
    'first_name', 'last_name', 'phone', 'address', 'emergency_contact_name',
    'emergency_contact_phone', 'bio', 'skills', 'photo',
}
HR_GRANTABLE_ROLES = {'guest', 'employee', 'manager'}


def validate_photo_file(f):
    if f and f.size > MAX_PHOTO_BYTES:
        raise serializers.ValidationError('Image must be 3 MB or smaller.')
    if f:
        # Pillow accepts image/HTML polyglots; the extension decides the Content-Type /media is served with.
        try:
            validate_image_file_extension(f)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
    return f


def user_brief(user, request=None):
    """{id, full_name, designation, photo, role} — org-chart / manager card."""
    if user is None:
        return None
    p = getattr(user, 'profile', None)
    photo = None
    if p and p.photo:
        photo = request.build_absolute_uri(p.photo.url) if request else p.photo.url
    return {
        'id': user.id,
        'full_name': user.full_name,
        'designation': p.designation if p else '',
        'photo': photo,
        'role': user.role,
    }


# ---------------------------------------------------------------- Organization

class OrganizationSerializer(serializers.ModelSerializer):
    weekend_days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6), required=False, max_length=7,
    )

    class Meta:
        model = Organization
        fields = [
            'name', 'tagline', 'about', 'logo', 'email', 'phone', 'address', 'website',
            'github', 'linkedin', 'youtube', 'founded',
            'work_start', 'work_end', 'late_grace_minutes', 'weekend_days', 'updated_at',
        ]
        read_only_fields = ['updated_at']

    def validate_logo(self, f):
        return validate_photo_file(f)

    def validate_weekend_days(self, days):
        if len(set(days)) != len(days):
            raise serializers.ValidationError('Weekend days must be unique (0=Monday … 6=Sunday).')
        if len(days) >= 7:
            raise serializers.ValidationError('At least one working day is required.')
        return sorted(days)

    def validate(self, attrs):
        user = self.context['request'].user
        policy = [f for f in WORK_POLICY_FIELDS if f in attrs]
        if policy and not user.has_role('super_admin'):
            raise PermissionDenied(f'Only a super admin may change work policy: {", ".join(policy)}.')
        start = attrs.get('work_start', self.instance.work_start if self.instance else None)
        end = attrs.get('work_end', self.instance.work_end if self.instance else None)
        if start and end and start >= end:
            raise serializers.ValidationError({'work_end': 'Work end must be after work start.'})
        return attrs


# ---------------------------------------------------------------- Departments

class DepartmentSerializer(serializers.ModelSerializer):
    manager = serializers.SerializerMethodField()
    manager_id = serializers.PrimaryKeyRelatedField(
        source='manager', queryset=User.objects.filter(is_active=True),
        allow_null=True, required=False, write_only=True,
    )
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'name', 'description', 'parent', 'manager', 'manager_id', 'member_count', 'created_at']
        read_only_fields = ['created_at']

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_manager(self, obj):
        return {'id': obj.manager_id, 'full_name': obj.manager.full_name} if obj.manager else None

    def validate_manager_id(self, user):
        if user and not user.has_role('employee'):
            raise serializers.ValidationError('Department manager must be staff (employee role or higher).')
        return user

    def validate_parent(self, parent):
        if (self.instance or Department()).creates_cycle(parent):
            raise serializers.ValidationError(
                'A department cannot be its own parent or a child of one of its sub-departments.'
            )
        return parent


# ---------------------------------------------------------------- People

class PersonSerializer(serializers.ModelSerializer):
    """User + EmployeeProfile, flattened. Profile fields use source='profile.*'."""

    full_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False, style={'input_type': 'password'})

    department = serializers.SerializerMethodField()
    department_id = serializers.PrimaryKeyRelatedField(
        source='profile.department', queryset=Department.objects.all(),
        allow_null=True, required=False, write_only=True,
    )
    manager = serializers.SerializerMethodField()
    employee_code = serializers.CharField(source='profile.employee_code', required=False, allow_blank=True, max_length=30)
    designation = serializers.CharField(source='profile.designation', required=False, allow_blank=True, max_length=120)
    employment_type = serializers.ChoiceField(
        source='profile.employment_type', choices=EmployeeProfile.EmploymentType.choices, required=False,
    )
    join_date = serializers.DateField(source='profile.join_date', required=False, allow_null=True)
    date_of_birth = serializers.DateField(source='profile.date_of_birth', required=False, allow_null=True)
    phone = serializers.CharField(source='profile.phone', required=False, allow_blank=True, max_length=30)
    address = serializers.CharField(source='profile.address', required=False, allow_blank=True, max_length=255)
    emergency_contact_name = serializers.CharField(
        source='profile.emergency_contact_name', required=False, allow_blank=True, max_length=120,
    )
    emergency_contact_phone = serializers.CharField(
        source='profile.emergency_contact_phone', required=False, allow_blank=True, max_length=30,
    )
    photo = serializers.ImageField(source='profile.photo', required=False, allow_null=True)
    bio = serializers.CharField(source='profile.bio', required=False, allow_blank=True)
    skills = serializers.ListField(
        source='profile.skills', child=serializers.CharField(max_length=60), required=False, max_length=50,
    )
    visibility = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'is_active', 'password',
            'department', 'department_id', 'manager', 'employee_code', 'designation', 'employment_type',
            'join_date', 'date_of_birth', 'phone', 'address', 'emergency_contact_name',
            'emergency_contact_phone', 'photo', 'bio', 'skills', 'visibility',
        ]
        read_only_fields = ['id', 'is_active']
        extra_kwargs = {'role': {'required': False}}

    # -- representation -------------------------------------------------------

    def _full_view(self, user):
        """Full profile for self, hr_admin+, and the user's manager; else directory subset."""
        viewer = self.context['request'].user
        if viewer.pk == user.pk or viewer.has_role('hr_admin'):
            return True
        if user.has_role('hr_admin'):  # a dept manager never gets HR/super admin private data
            return False
        p = getattr(user, 'profile', None)
        return bool(p and p.manager and p.manager.pk == viewer.pk)

    def to_representation(self, user):
        if getattr(user, 'profile', None) is None:
            user.profile = EmployeeProfile(user=user)  # transient, unsaved: keeps one response shape for guests
        data = super().to_representation(user)
        if not self._full_view(user):
            for f in SENSITIVE_FIELDS:
                data.pop(f, None)
        return data

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_department(self, user):
        p = getattr(user, 'profile', None)
        return {'id': p.department_id, 'name': p.department.name} if p and p.department else None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_manager(self, user):
        p = getattr(user, 'profile', None)
        m = p.manager if p else None
        return {'id': m.id, 'full_name': m.full_name} if m else None

    @extend_schema_field(serializers.ChoiceField(choices=['full', 'directory']))
    def get_visibility(self, user):
        return 'full' if self._full_view(user) else 'directory'

    # -- validation -----------------------------------------------------------

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_photo(self, f):
        return validate_photo_file(f)

    def validate_skills(self, skills):
        return list(dict.fromkeys(s.strip() for s in skills if s.strip()))

    def to_internal_value(self, data):
        # Edit rights are checked before field validation, so a 400 (e.g. "email already exists")
        # never leaks to someone who may not make the edit at all.
        if isinstance(data, Mapping):
            self._check_edit_rights(data)
        return super().to_internal_value(data)

    def _check_edit_rights(self, data):
        actor, target = self.context['request'].user, self.instance
        if target is None:  # create: the view restricts it to hr_admin+
            return
        if actor.has_role('hr_admin'):
            if target.has_role('hr_admin') and not actor.has_role('super_admin') and actor.pk != target.pk:
                raise PermissionDenied('Only a super admin may edit an HR admin or super admin account.')
            return
        if actor.pk != target.pk:
            raise PermissionDenied('You can only edit your own profile.')
        sent = {k for k in data if k in self.fields and not self.fields[k].read_only}
        if data.get('role') == target.role:
            sent.discard('role')  # unchanged role is a no-op
        forbidden = sorted(sent - SELF_EDITABLE)
        if forbidden:
            raise PermissionDenied(
                f'You cannot change these fields on your own profile: {", ".join(forbidden)}. '
                'Ask HR to update them.'
            )

    def validate(self, attrs):
        actor = self.context['request'].user
        target = self.instance

        if 'password' in attrs:
            # HR sets an initial password or resets someone else's (edit rights checked above);
            # your own goes through POST people/me/password/ with the current password.
            if target is not None and target.pk == actor.pk:
                raise serializers.ValidationError({'password': 'Use "Change password" to change your own password.'})
            try:
                validate_password(attrs['password'], user=target)
            except DjangoValidationError as e:
                raise serializers.ValidationError({'password': list(e.messages)})
        if target is None:  # create
            attrs.setdefault('role', User.Role.EMPLOYEE)

        if 'role' in attrs:
            self._check_role_change(actor, target, attrs['role'])
        return attrs

    def _check_role_change(self, actor, target, new_role):
        if target is not None and target.role == new_role:
            return
        if target is not None and target.pk == actor.pk:
            raise PermissionDenied('You cannot change your own role.')
        if not actor.has_role('hr_admin'):
            raise PermissionDenied('Only HR admins can change roles.')
        if not actor.has_role('super_admin'):
            if new_role not in HR_GRANTABLE_ROLES:
                raise PermissionDenied('Only a super admin can grant the HR admin or super admin role.')
            if target is not None and target.has_role('hr_admin'):
                raise PermissionDenied('Only a super admin can change the role of an HR admin or super admin.')
        if target is not None and target.is_superuser and new_role != User.Role.SUPER_ADMIN:
            raise serializers.ValidationError(
                {'role': 'This account is a Django superuser and always has the super admin role.'}
            )

    # -- persistence ----------------------------------------------------------

    @transaction.atomic
    def create(self, validated):
        profile_attrs = validated.pop('profile', {})
        password = validated.pop('password', None)
        email = validated['email']
        base = email.split('@')[0][:140] or 'user'
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            n += 1
            username = f'{base}{n}'
        user = User(username=username, **validated)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()  # signal creates the profile for staff roles
        if profile_attrs:
            self._save_profile(user, profile_attrs)
        return user

    @transaction.atomic
    def update(self, user, validated):
        profile_attrs = validated.pop('profile', {})
        password = validated.pop('password', None)
        for k, v in validated.items():
            setattr(user, k, v)
        if password:
            user.set_password(password)
        user.save()
        if profile_attrs:
            self._save_profile(user, profile_attrs)
        return user

    def _save_profile(self, user, attrs):
        profile, _ = EmployeeProfile.objects.get_or_create(user=user)
        for k, v in attrs.items():
            setattr(profile, k, '' if (k == 'photo' and v is None) else v)
        profile.save()
        user.profile = profile  # refresh the cached relation for the response


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, user=self.context['request'].user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

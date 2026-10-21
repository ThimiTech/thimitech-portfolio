from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.permissions.permissions import IsEmployee, IsHRAdmin
from apps.users.throttles import PasswordThrottle

from .models import Department, Organization
from .serializers import (
    DepartmentSerializer, OrganizationSerializer, PasswordChangeSerializer, PersonSerializer, user_brief,
)

User = get_user_model()
TAG = ['Org & staff profiles']
STAFF_ROLES = [r for r in User.RANK if User.RANK[r] >= User.RANK['employee']]
PARSERS = [JSONParser, MultiPartParser, FormParser]


def _flag(request, name):
    return request.query_params.get(name, '').lower() in ('1', 'true', 'yes')


@extend_schema(tags=TAG)
class OrganizationViewSet(viewsets.GenericViewSet):
    """Singleton org profile + work policy. GET employee+, PATCH hr_admin+ (policy fields super_admin)."""

    serializer_class = OrganizationSerializer
    parser_classes = PARSERS

    def get_permissions(self):
        return [IsHRAdmin()] if self.request.method not in ('GET', 'HEAD', 'OPTIONS') else [IsEmployee()]

    def get_object(self):
        return Organization.load()

    @extend_schema(summary='Organization profile & work policy')
    def retrieve(self, request):
        return Response(self.get_serializer(self.get_object()).data)

    @extend_schema(summary='Update organization (work policy: super_admin only)')
    def partial_update(self, request):
        s = self.get_serializer(self.get_object(), data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


@extend_schema_view(
    list=extend_schema(summary='List departments'),
    retrieve=extend_schema(summary='Department detail'),
    create=extend_schema(summary='Create department (hr_admin+)'),
    partial_update=extend_schema(summary='Update department (hr_admin+)'),
    update=extend_schema(summary='Replace department (hr_admin+)'),
    destroy=extend_schema(summary='Delete department (hr_admin+); members become unassigned'),
)
@extend_schema(tags=TAG)
class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        return [IsEmployee()] if self.action in ('list', 'retrieve') else [IsHRAdmin()]

    def get_queryset(self):
        return Department.objects.select_related('manager').annotate(
            member_count=Count('members', filter=Q(members__user__is_active=True, members__user__role__in=STAFF_ROLES))
        )


@extend_schema(tags=TAG)
class StructureView(APIView):
    """Nested department tree for the org chart, plus staff without a department."""

    permission_classes = [IsEmployee]

    @extend_schema(summary='Org chart: nested departments with manager + members', responses=OpenApiTypes.OBJECT)
    def get(self, request):
        depts = list(Department.objects.select_related('manager__profile'))
        staff = User.objects.filter(is_active=True, role__in=STAFF_ROLES).select_related('profile').order_by(
            'first_name', 'email'
        )
        members, unassigned = {}, []
        for u in staff:
            p = getattr(u, 'profile', None)
            if p and p.department_id:
                members.setdefault(p.department_id, []).append(user_brief(u, request))
            else:
                unassigned.append(user_brief(u, request))

        nodes = {
            d.id: {
                'id': d.id, 'name': d.name, 'description': d.description, 'parent': d.parent_id,
                'manager': user_brief(d.manager, request), 'members': members.get(d.id, []), 'children': [],
            }
            for d in depts
        }
        parent_of = {d.id: d.parent_id for d in depts}

        def on_loop(i):  # legacy parent loops (pre-validation / raw ORM) would otherwise vanish from the chart
            seen, j = set(), parent_of[i]
            while j in parent_of and j not in seen:
                if j == i:
                    return True
                seen.add(j)
                j = parent_of[j]
            return False

        roots = []
        for d in depts:
            attach = d.parent_id in nodes and not on_loop(d.id)
            (nodes[d.parent_id]['children'] if attach else roots).append(nodes[d.id])
        return Response({'departments': roots, 'unassigned': unassigned})


people_filters = [
    OpenApiParameter('search', str, description='Matches name, email or designation (all words must match).'),
    OpenApiParameter('department', int, description='Department id.'),
    OpenApiParameter('role', str, enum=[r for r in User.Role.values]),
    OpenApiParameter('include_guests', bool, description='hr_admin+ only: also list guest users.'),
    OpenApiParameter('is_active', bool, description='hr_admin+ only: filter by active state (default: all for HR).'),
]


@extend_schema_view(
    list=extend_schema(summary='Staff directory', parameters=people_filters),
    retrieve=extend_schema(summary='Person profile (full for self / HR / their manager; directory subset otherwise)'),
    create=extend_schema(summary='Onboard a person: creates User + profile (hr_admin+)'),
    partial_update=extend_schema(summary='Update person (self: contact fields; hr_admin+: all)'),
)
@extend_schema(tags=TAG)
class PersonViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                    mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """Staff directory and profiles. Never hard-deletes: use deactivate/reactivate."""

    serializer_class = PersonSerializer
    parser_classes = PARSERS
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('create', 'deactivate', 'reactivate'):
            return [IsHRAdmin()]
        return [IsEmployee()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # OpenAPI schema generation
            return User.objects.none()
        req, user = self.request, self.request.user
        qs = User.objects.select_related('profile__department__manager').order_by('first_name', 'last_name', 'email')
        is_hr = user.has_role('hr_admin')
        # Guests are hidden from the directory; HR sees them on detail routes or with ?include_guests=1.
        if not is_hr or (self.action == 'list' and not _flag(req, 'include_guests')):
            qs = qs.filter(role__in=STAFF_ROLES)
        if not is_hr:
            qs = qs.filter(is_active=True)
        elif 'is_active' in req.query_params:
            qs = qs.filter(is_active=_flag(req, 'is_active'))

        if self.action == 'list':
            for term in req.query_params.get('search', '').split():
                qs = qs.filter(
                    Q(first_name__icontains=term) | Q(last_name__icontains=term)
                    | Q(email__icontains=term) | Q(profile__designation__icontains=term)
                )
            dept = req.query_params.get('department')
            if dept:
                if not dept.isdigit():
                    raise ValidationError({'department': 'Must be a department id.'})
                qs = qs.filter(profile__department_id=dept)
            role = req.query_params.get('role')
            if role:
                if role not in User.Role.values:
                    raise ValidationError({'role': f'Must be one of: {", ".join(User.Role.values)}.'})
                qs = qs.filter(role=role)
        return qs

    @extend_schema(summary='My own full profile (GET) / update own contact fields (PATCH)',
                   request=PersonSerializer, responses=PersonSerializer)
    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        self.kwargs['pk'] = request.user.pk
        if request.method == 'PATCH':
            return self.partial_update(request, pk=request.user.pk)
        return self.retrieve(request, pk=request.user.pk)

    @extend_schema(summary='Change my own password (needs the current one)', request=PasswordChangeSerializer,
                   responses={204: None})
    @action(detail=False, methods=['post'], url_path='me/password', serializer_class=PasswordChangeSerializer,
            throttle_classes=[PasswordThrottle])
    def change_password(self, request):
        s = PasswordChangeSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        request.user.set_password(s.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response(status=204)

    def _set_active(self, request, active):
        target = self.get_object()
        if target.pk == request.user.pk:
            raise PermissionDenied('You cannot change the active state of your own account.')
        if target.has_role('hr_admin') and not request.user.has_role('super_admin'):
            raise PermissionDenied('Only a super admin may deactivate or reactivate an HR admin or super admin.')
        target.is_active = active
        target.save(update_fields=['is_active'])
        return Response(self.get_serializer(target).data)

    @extend_schema(summary='Deactivate account (hr_admin+). Never deletes.', request=None, responses=PersonSerializer)
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        return self._set_active(request, False)

    @extend_schema(summary='Reactivate account (hr_admin+)', request=None, responses=PersonSerializer)
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        return self._set_active(request, True)

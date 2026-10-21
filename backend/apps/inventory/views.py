from django.db import transaction
from django.db.models import F, Prefetch
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.notifications.services import push
from config.pagination import ServerListMixin
from apps.leave.services import hr_users
from apps.permissions.permissions import IsEmployee, IsHRAdmin
from .models import Category, Asset, Assignment
from .services import summary_payload
from .serializers import IssueReportSerializer, MyAssignmentSerializer, CategorySerializer, AssetSerializer, AssignmentSerializer, ReturnSerializer, InventorySummarySerializer


@extend_schema(tags=['Inventory'])
class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsHRAdmin]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('Move the assets to another category before deleting this one.')


@extend_schema(tags=['Inventory'])
class AssetViewSet(ServerListMixin, viewsets.ModelViewSet):
    permission_classes = [IsHRAdmin]
    serializer_class = AssetSerializer
    search_fields = ['tag', 'name', 'serial_number', 'location', 'category__name']
    ordering_fields = ['tag', 'name', 'status', 'category__name', 'purchase_date']
    status_choices = [c for c, _ in Asset._meta.get_field('status').choices]

    def get_queryset(self):
        qs = Asset.objects.select_related('category').prefetch_related(Prefetch('assignments', queryset=Assignment.objects.filter(returned_at__isnull=True).select_related('employee')))
        if self.request.method not in ('GET', 'HEAD', 'OPTIONS'):
            qs = qs.select_for_update()
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        asset = self.get_object()
        if Assignment.objects.filter(asset=asset).exists():
            raise ValidationError('Retire assets with assignment history instead of deleting them.')
        return super().destroy(request, *args, **kwargs)


@extend_schema(tags=['Inventory'])
class AssignmentViewSet(ServerListMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsHRAdmin]
    serializer_class = AssignmentSerializer
    search_fields = ['asset__tag', 'asset__name', 'employee__first_name', 'employee__last_name', 'employee__email']
    ordering_fields = ['assigned_at', 'due_back', 'returned_at', 'asset__tag', 'employee__first_name']

    def get_queryset(self):
        qs = Assignment.objects.select_related('employee', 'asset')
        asset = self.request.query_params.get('asset')
        if asset:
            if not asset.isdigit():
                raise ValidationError({'asset': 'Use an asset id.'})
            qs = qs.filter(asset_id=asset)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        asset = Asset.objects.select_for_update().get(pk=serializer.validated_data['asset'].pk)
        if asset.status != 'available' or asset.assignments.filter(returned_at__isnull=True).exists():
            raise ValidationError({'asset': 'Only available assets can be assigned.'})
        assignment = serializer.save(assigned_by=self.request.user)
        due = f' Please return it by {assignment.due_back:%d %b %Y}.' if assignment.due_back else ''
        push([assignment.employee], 'asset_assigned', f'{asset.name} ({asset.tag}) was assigned to you',
             f'Handed over by {self.request.user.full_name}.{due}', '/app/my-assets', exclude=self.request.user)
        asset.status = 'assigned'
        asset.save(update_fields=['status', 'updated_at'])

    @extend_schema(request=ReturnSerializer, responses=AssignmentSerializer)
    @action(detail=True, methods=['post'], url_path='return')
    @transaction.atomic
    def return_asset(self, request, pk=None):
        current = self.get_object()
        asset = Asset.objects.select_for_update().get(pk=current.asset_id)
        assignment = Assignment.objects.select_for_update().get(pk=current.pk)
        if assignment.returned_at:
            raise ValidationError('This assignment has already been returned.')
        data = ReturnSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        assignment.returned_at = timezone.now()
        assignment.returned_by = request.user
        assignment.return_note = data.validated_data['return_note']
        assignment.return_condition = data.validated_data['condition']
        assignment.save(update_fields=['returned_at', 'returned_by', 'return_note', 'return_condition'])
        asset.status = assignment.return_condition
        asset.save(update_fields=['status', 'updated_at'])
        return Response(self.get_serializer(assignment).data)


@extend_schema(tags=['Inventory'])
class MyAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    """My assets: the caller's own assignments, current (returned_at null) first, then history."""
    permission_classes = [IsEmployee]
    serializer_class = MyAssignmentSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Assignment.objects.none()
        return (Assignment.objects.filter(employee=self.request.user).select_related('asset__category')
                .order_by(F('returned_at').desc(nulls_first=True), '-assigned_at'))

    @extend_schema(request=IssueReportSerializer, responses={204: None},
                   summary='Report a problem with an asset you currently hold (notifies HR)')
    @action(detail=True, methods=['post'], url_path='report-issue')
    def report_issue(self, request, pk=None):
        assignment = self.get_object()
        if assignment.returned_at:
            raise ValidationError('You have returned this asset; contact HR directly.')
        data = IssueReportSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        asset = assignment.asset
        # ponytail: notification-only, no issue table; add a model if HR needs to track/resolve issues.
        push(hr_users(), 'asset_issue', f'{request.user.full_name} reported an issue with {asset.name} ({asset.tag})',
             data.validated_data['note'], '/app/inventory', exclude=request.user)
        return Response(status=204)


@extend_schema(tags=['Inventory'])
class SummaryView(APIView):
    permission_classes = [IsHRAdmin]

    @extend_schema(responses=InventorySummarySerializer)
    def get(self, request):
        return Response(summary_payload())

import datetime
from django.apps import apps
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.permissions.permissions import IsSuperAdmin
from .models import AuditLog
from .policy import tracked
from .serializers import AuditLogSerializer, AuditFiltersSerializer, AuditOptionsSerializer, MonitoringWindowSerializer
from .monitoring_serializers import MonitoringSerializer


class AuditPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


@extend_schema(tags=['Audit trail'])
class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSuperAdmin]
    serializer_class = AuditLogSerializer
    pagination_class = AuditPagination

    @extend_schema(parameters=[AuditFiltersSerializer])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        serializer = AuditFiltersSerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        qs = AuditLog.objects.all()
        if 'module' in params:
            labels = [m._meta.label_lower for m in apps.get_models() if tracked(m) and m._meta.app_label == params['module']]
            qs = qs.filter(target_model__in=labels)
        for field, lookup in [('action', 'action'), ('source', 'source'), ('actor', 'actor_id'), ('request_id', 'request_id')]:
            if field in params:
                qs = qs.filter(**{lookup: params[field]})
        if 'start' in params:
            qs = qs.filter(timestamp__gte=timezone.make_aware(datetime.datetime.combine(params['start'], datetime.time.min)))
        if 'end' in params:
            qs = qs.filter(timestamp__lt=timezone.make_aware(datetime.datetime.combine(params['end'] + datetime.timedelta(days=1), datetime.time.min)))
        if params.get('search'):
            term = params['search']
            qs = qs.filter(Q(actor_label__icontains=term) | Q(target_model__icontains=term) | Q(target_id=term))
        return qs


@extend_schema(tags=['Audit trail'])
class OptionsView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(responses=AuditOptionsSerializer)
    def get(self, request):
        models = sorted(m._meta.label_lower for m in apps.get_models() if tracked(m))
        return Response({'modules': sorted({name.split('.')[0] for name in models}), 'actions': AuditLog.Action.values, 'sources': ['api', 'admin', 'system'], 'tracked_models': models, 'capture_started_at': AuditLog.objects.order_by('timestamp', 'id').values_list('timestamp', flat=True).first()})


@extend_schema(tags=['Organization monitoring'])
class MonitoringView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(parameters=[MonitoringWindowSerializer], responses=MonitoringSerializer)
    def get(self, request):
        from .monitoring import overview
        serializer = MonitoringWindowSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(overview(**serializer.validated_data))

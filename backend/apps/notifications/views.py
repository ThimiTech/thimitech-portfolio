from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view, inline_serializer
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer

TAGS = ['Notifications']
LIST_CAP = 50  # ponytail: newest 50 only; add pagination if people need to scroll further back


@extend_schema_view(
    list=extend_schema(tags=TAGS, summary=f'My notifications, newest first (max {LIST_CAP})', parameters=[
        OpenApiParameter('unread', OpenApiTypes.BOOL, description='1 = unread only'),
    ]),
)
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Strictly the caller's own inbox: every route is scoped to recipient=request.user."""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user)

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        if request.query_params.get('unread', '').lower() in ('1', 'true', 'yes'):
            qs = qs.filter(read_at__isnull=True)
        return Response(self.get_serializer(qs[:LIST_CAP], many=True).data)

    @extend_schema(tags=TAGS, responses=inline_serializer('NotificationUnread', {'unread': serializers.IntegerField()}))
    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        return Response({'unread': self.get_queryset().filter(read_at__isnull=True).count()})

    @extend_schema(tags=TAGS, request=None, responses=NotificationSerializer)
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        n = self.get_object()  # 404 for anyone else's notification
        if n.read_at is None:
            n.read_at = timezone.now()
            n.save(update_fields=['read_at'])
        return Response(self.get_serializer(n).data)

    @extend_schema(tags=TAGS, request=None, responses=inline_serializer('NotificationReadAll', {'marked': serializers.IntegerField()}))
    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        return Response({'marked': self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())})

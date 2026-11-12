from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.notices.serializers import user_brief
from apps.notifications.services import push
from apps.permissions.permissions import IsManager
from apps.users.throttles import ClientIPThrottle
from config.pagination import ServerListMixin

from .models import Inquiry

User = get_user_model()
INBOX_ROLES = ('manager', 'hr_admin', 'super_admin')


class InquiryThrottle(ClientIPThrottle):
    scope = 'inquiry'


class PublicInquirySerializer(serializers.ModelSerializer):
    # Honeypot: hidden from people, filled by bots. A filled one is accepted and dropped.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Inquiry
        fields = ['name', 'email', 'phone', 'company', 'message', 'website']
        extra_kwargs = {'message': {'min_length': 10}}


class InquirySerializer(serializers.ModelSerializer):
    assignee_detail = serializers.SerializerMethodField()
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True, role__in=INBOX_ROLES), allow_null=True, required=False)

    class Meta:
        model = Inquiry
        fields = ['id', 'name', 'email', 'phone', 'company', 'message', 'status', 'assignee', 'assignee_detail',
                  'note', 'created_at', 'updated_at']
        read_only_fields = ['id', 'name', 'email', 'phone', 'company', 'message', 'created_at', 'updated_at']

    def get_assignee_detail(self, obj) -> dict | None:
        return user_brief(obj.assignee, self.context['request']) if obj.assignee else None


@extend_schema(tags=['Inquiries'])
class InquiryViewSet(ServerListMixin, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """POST is the public contact form (no auth, throttled). Everything else is the manager+ inbox."""
    queryset = Inquiry.objects.select_related('assignee__profile')
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    search_fields = ['name', 'email', 'company', 'message']
    ordering_fields = ['created_at', 'status', 'name']
    status_choices = Inquiry.Status.values

    def get_permissions(self):
        return [AllowAny()] if self.action == 'create' else [IsManager()]

    def get_throttles(self):
        return [InquiryThrottle()] if self.action == 'create' else []

    def get_authenticators(self):
        # A visitor with a stale token in localStorage must still be able to send the form.
        return [] if self.request and self.request.method == 'POST' else super().get_authenticators()

    def get_serializer_class(self):
        return PublicInquirySerializer if self.action == 'create' else InquirySerializer

    @extend_schema(summary='Send a message from the public contact form', responses={201: None})
    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        if not s.validated_data.pop('website', ''):
            inquiry = Inquiry.objects.create(**s.validated_data)
            push(User.objects.filter(is_active=True, role__in=INBOX_ROLES), 'inquiry',
                 f'New inquiry from {inquiry.name}', inquiry.message[:200], f'/app/inquiries?open={inquiry.pk}')
        return Response(status=201)

    def perform_update(self, serializer):
        before = serializer.instance.assignee_id
        inquiry = serializer.save()
        if inquiry.assignee_id and inquiry.assignee_id != before:
            push([inquiry.assignee], 'inquiry', f'An inquiry from {inquiry.name} was assigned to you',
                 link=f'/app/inquiries?open={inquiry.pk}', exclude=self.request.user)

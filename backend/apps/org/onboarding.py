"""Onboarding checklists: HR keeps one template; each new hire gets their own copy to tick off."""
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.permissions.permissions import IsEmployee, IsHRAdmin

from .models import OnboardingStep, OnboardingTask

TAG = ['Onboarding']


def start_onboarding(user):
    """Copy the active template steps to `user`. Does nothing if they already have a checklist."""
    if OnboardingTask.objects.filter(user=user).exists():
        return 0
    return len(OnboardingTask.objects.bulk_create(
        OnboardingTask(user=user, title=s.title, description=s.description, position=s.position)
        for s in OnboardingStep.objects.filter(is_active=True)))


class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingStep
        fields = ['id', 'title', 'description', 'position', 'is_active']


class TaskSerializer(serializers.ModelSerializer):
    done = serializers.SerializerMethodField()
    done_by_name = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingTask
        fields = ['id', 'user', 'title', 'description', 'position', 'done', 'done_at', 'done_by_name']

    def get_done(self, obj) -> bool:
        return obj.done_at is not None

    def get_done_by_name(self, obj) -> str:
        return obj.done_by.full_name if obj.done_by else ''


@extend_schema(tags=TAG)
class StepViewSet(viewsets.ModelViewSet):
    permission_classes = [IsHRAdmin]
    serializer_class = StepSerializer
    queryset = OnboardingStep.objects.all()


@extend_schema(tags=TAG)
class TaskViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """`GET ?user=` lists a checklist (default: mine). You see your own; HR sees anyone's;
    a manager sees their department's. The owner or HR ticks steps."""
    permission_classes = [IsEmployee]
    serializer_class = TaskSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OnboardingTask.objects.none()
        me = self.request.user
        qs = OnboardingTask.objects.select_related('done_by')
        if not me.has_role('hr_admin'):
            qs = qs.filter(user=me) | qs.filter(user__profile__department__manager=me)
        if self.action != 'list':
            return qs
        target = self.request.query_params.get('user', str(me.pk))
        if not target.isdigit():
            raise ValidationError({'user': 'Use a user id.'})
        return qs.filter(user_id=target)

    @extend_schema(request=None, responses=TaskSerializer, summary='Tick or untick a step (the owner, or HR)')
    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        task = self.get_object()
        if task.user_id != request.user.pk and not request.user.has_role('hr_admin'):
            raise PermissionDenied('Only the person themselves or HR can tick this off.')
        task.done_at, task.done_by = (None, None) if task.done_at else (timezone.now(), request.user)
        task.save(update_fields=['done_at', 'done_by'])
        return Response(self.get_serializer(task).data)

    @extend_schema(request=inline_serializer('OnboardingStart', {'user': serializers.IntegerField()}),
                   responses=TaskSerializer(many=True), summary='Give someone the checklist (hr_admin+)')
    @action(detail=False, methods=['post'], permission_classes=[IsHRAdmin])
    def start(self, request):
        pk = str(request.data.get('user', ''))
        user = get_user_model().objects.filter(pk=pk, is_active=True).first() if pk.isdigit() else None
        if not user or not user.has_role('employee'):
            raise ValidationError({'user': 'Pick an active staff member.'})
        if not start_onboarding(user):
            raise ValidationError('They already have a checklist, or the template has no active steps.')
        return Response(TaskSerializer(OnboardingTask.objects.filter(user=user), many=True).data, status=201)

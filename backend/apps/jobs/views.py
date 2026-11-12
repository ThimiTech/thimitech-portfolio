import os

from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.permissions.permissions import IsHRAdmin
from config.pagination import ServerListMixin

from . import services
from .models import Job, JobApplication
from .serializers import (HireSerializer, HiringApplicationSerializer, HiringJobSerializer,
                          JobApplicationSerializer, JobSerializer)

STATUSES = [c for c, _ in JobApplication.STATUS_CHOICES]


@extend_schema(tags=['Jobs'])
class JobViewSet(viewsets.ModelViewSet):
    """Public: active postings (list/detail), apply, my applications. HR: every posting, plus create/edit/delete."""
    lookup_value_regex = r'\d+'
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        if self.action in ('apply', 'applications'):
            return [IsAuthenticated()]
        return [IsHRAdmin()]

    def _manage(self):
        """HR managing postings. The hiring page sends ?manage=1 on reads; the public site keeps its plain,
        active-only shape even when the visitor happens to be signed in as HR."""
        user = self.request.user
        if not (user.is_authenticated and user.has_role('hr_admin')):
            return False
        return self.request.method != 'GET' or 'manage' in self.request.query_params

    def get_serializer_class(self):
        if self.action in ('apply', 'applications'):
            return JobApplicationSerializer
        return HiringJobSerializer if self._manage() else JobSerializer

    def get_queryset(self):
        qs = Job.objects.prefetch_related('requirements')
        if not self._manage():
            return qs.filter(is_active=True)
        return qs.annotate(application_count=Count('applications'),
                           pending_count=Count('applications', filter=Q(applications__status='pending')))

    def perform_create(self, serializer):
        serializer.instance = self.get_queryset().get(pk=serializer.save().pk)  # re-read with the counts

    def perform_update(self, serializer):
        serializer.instance = self.get_queryset().get(pk=serializer.save().pk)

    def perform_destroy(self, instance):
        if instance.application_count:
            raise ValidationError('This posting has applications. Close it instead of deleting it.')
        instance.delete()

    @extend_schema(summary='Apply for a job', request=JobApplicationSerializer, responses={201: JobApplicationSerializer})
    @action(detail=False, methods=['post'])
    def apply(self, request):
        serializer = JobApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if JobApplication.objects.filter(job=serializer.validated_data['job'], applicant=request.user).exists():
            return Response({'error': 'You have already applied for this job.'}, status=400)
        application = serializer.save(applicant=request.user)
        services.announce_new(application)
        return Response(serializer.data, status=201)

    @extend_schema(summary='List my job applications', responses=JobApplicationSerializer(many=True))
    @action(detail=False, methods=['get'])
    def applications(self, request):
        mine = JobApplication.objects.filter(applicant=request.user).select_related('job')
        return Response(JobApplicationSerializer(mine, many=True, context={'request': request}).data)


@extend_schema(tags=['Hiring'])
class HiringApplicationViewSet(ServerListMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                               mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """HR pipeline: review applications, move them between stages, read the CV, hire."""
    permission_classes = [IsHRAdmin]
    serializer_class = HiringApplicationSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']
    search_fields = ['name', 'applicant__email', 'phone', 'job__title']
    ordering_fields = ['applied_at', 'name', 'status', 'job__title']
    status_choices = STATUSES

    def get_queryset(self):
        qs = JobApplication.objects.select_related('job', 'applicant')
        job = self.request.query_params.get('job')
        if job:
            if not job.isdigit():
                raise ValidationError({'job': 'Use a job id.'})
            qs = qs.filter(job_id=job)
        return qs

    def perform_update(self, serializer):
        before = serializer.instance.status
        application = serializer.save()
        if application.status != before:
            services.announce_status(application)

    @extend_schema(summary='Download the CV', responses={(200, 'application/octet-stream'): OpenApiTypes.BINARY})
    @action(detail=True, methods=['get'])
    def cv(self, request, pk=None):
        application = self.get_object()
        try:
            fh = application.cv.open('rb')
        except (FileNotFoundError, ValueError):
            raise Http404
        return FileResponse(fh, as_attachment=True, filename=os.path.basename(application.cv.name))

    @extend_schema(summary='Hire: make the applicant an employee and start their onboarding',
                   request=HireSerializer, responses=HiringApplicationSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def hire(self, request, pk=None):
        application = self.get_object()
        if application.status == 'rejected':
            raise ValidationError('This application was rejected. Move it back to a live stage first.')
        if not application.applicant.is_active:
            raise ValidationError('The account behind this application is deactivated.')
        data = HireSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        was_selected = application.status == 'selected'
        services.hire(application, **data.validated_data)
        if not was_selected:
            services.announce_status(application)
        return Response(self.get_serializer(application).data)

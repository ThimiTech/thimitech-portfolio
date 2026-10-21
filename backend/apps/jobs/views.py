from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Job, JobApplication
from .serializers import JobSerializer, JobApplicationSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(
    tags=['Jobs'],
    summary='List active jobs',
    description='Returns all currently active job vacancies.',
    responses={
        200: JobSerializer(many=True),
    },
)
@api_view(['GET'])
def job_list(request):
    jobs = Job.objects.filter(is_active=True)
    serializer = JobSerializer(jobs, many=True)

    return Response(serializer.data)

@extend_schema(
    tags=['Jobs'],
    summary='Get job details',
    description='Returns details of a single job by ID.',
    responses={
        200: JobSerializer,
        404: {'description': 'Job not found.'},
    },
)
@api_view(['GET'])
def job_detail(request, pk):
    try:
        job = Job.objects.get(pk=pk, is_active=True)
    except Job.DoesNotExist:
        return Response(
            {"error": "Job not found"},
            status=404
        )

    serializer = JobSerializer(job)
    return Response(serializer.data)


@extend_schema(
    tags=['Jobs'],
    summary='Apply for a job',
    description=(
        "Allows an authenticated user to submit a job application. "
        "The applicant is automatically taken from the authenticated user."
    ),
    request=JobApplicationSerializer,
   responses={
    201: JobApplicationSerializer,
    400: {
        "description": (
            "Invalid application data or the user has already "
            "applied for this job."
        )
    },
    401: {
        "description": "Authentication credentials were not provided."
    },
},
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_job(request):
    serializer = JobApplicationSerializer(data=request.data)

    if serializer.is_valid():

        # Check if the user has already applied for this job
        if JobApplication.objects.filter(
            job=serializer.validated_data['job'],
            applicant=request.user
        ).exists():
            return Response(
                {"error": "You have already applied for this job."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.save(applicant=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

@extend_schema(
    tags=['Jobs'],
    summary='List my job applications',
    description=(
        'Returns all job applications submitted by the authenticated user.'
    ),
    responses={
        200: JobApplicationSerializer(many=True),
        401: {
            'description': 'Authentication credentials were not provided.'
        },
    },
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_applications(request):
    applications = JobApplication.objects.filter(
        applicant=request.user
    )

    serializer = JobApplicationSerializer(
        applications,
        many=True
    )

    return Response(serializer.data)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Job
from .serializers import JobSerializer, JobApplicationSerializer


@api_view(['GET'])
def job_list(request):
    jobs = Job.objects.filter(is_active=True)
    serializer = JobSerializer(jobs, many=True)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_for_job(request):
    serializer = JobApplicationSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(applicant=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )
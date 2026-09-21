from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Service, Project
from .serializers import ServiceSerializer, ProjectSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_list(request):
    services = Service.objects.all()
    serializer = ServiceSerializer(services, many=True)

    return Response(serializer.data)

@api_view(['GET'])
def project_list(request):
    projects = Project.objects.all()
    serializer = ProjectSerializer(projects, many=True)

    return Response(serializer.data)
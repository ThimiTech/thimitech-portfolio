

# Create your views here.
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiRequest

from .models import Project
from .serializers import ProjectSerializer
from apps.permissions.permissions import IsAdminOrReadOnly


@extend_schema(
    request=OpenApiRequest(
        request=ProjectSerializer,
        encoding={'image': {'contentType': 'image/*'}}
    ),
    responses=ProjectSerializer
)

@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAdminOrReadOnly])
def project_list(request):

    if request.method == 'GET':
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = ProjectSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)
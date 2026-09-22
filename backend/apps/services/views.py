from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Service
from .serializers import ServiceSerializer
from .permissions import IsAdminOrReadOnly

@extend_schema(
    request=ServiceSerializer,
    responses=ServiceSerializer
)

@api_view(['GET', 'POST'])
@permission_classes([IsAdminOrReadOnly])
def service_list(request):

    if request.method == 'GET':
        services = Service.objects.all()
        serializer = ServiceSerializer(services, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = ServiceSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

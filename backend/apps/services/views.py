from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import Service
from .serializers import ServiceSerializer
from apps.permissions.permissions import IsAdminOrReadOnly

@extend_schema_view(
    get=extend_schema(
        tags=['Services'],
        summary='List services',
        description='Returns all services.',
        responses={
            200: ServiceSerializer(many=True),
        },
    ),
    post=extend_schema(
        tags=['Services'],
        summary='Create a service',
        description='Allows staff users to create a new service.',
        request=ServiceSerializer,
        responses={
            201: ServiceSerializer,
            400: {
                'description': 'Invalid service data.'
            },
            403: {
                'description': 'Only staff users can create services.'
            }
        },
    ),
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

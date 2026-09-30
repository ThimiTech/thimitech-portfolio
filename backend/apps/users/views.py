

# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import RegisterSerializer
from drf_spectacular.utils import extend_schema


@extend_schema(
    tags=["Authentication"],
    summary="Register a new user",
    description=(
        "Creates a new user account using an email address and password. "
        "Username is optional; if it is not provided, it is generated "
        "from the email address."
    ),
    request=RegisterSerializer,
    responses={
        201: {
            "description": "User registered successfully."
        },
        400: {
            "description": "Invalid registration data."
        },
    },
)
@api_view(['POST'])
def register(request):
    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()

        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )
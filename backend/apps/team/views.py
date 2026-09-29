
# Create your views here.
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import TeamMember
from .serializers import TeamMemberSerializer
from drf_spectacular.utils import extend_schema

@extend_schema(
    summary="List active team members",
    description="Returns all active team members.",
    responses=TeamMemberSerializer(many=True),
)

@api_view(['GET'])
def team_list(request):
    team = TeamMember.objects.filter(is_active=True)
    serializer = TeamMemberSerializer(team, many=True)
    return Response(serializer.data)
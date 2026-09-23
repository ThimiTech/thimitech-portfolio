from rest_framework import serializers
from .models import TeamMember


class TeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamMember
        fields = [
            'id',
            'name',
            'role',
            'initials',
            'image',
            'email',
            'linkedin',
            'is_active',
            'display_order',
        ]
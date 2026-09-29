from rest_framework import serializers
from .models import TeamMember, SocialMedia


class SocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMedia
        fields = [
            'id',
            'platform',
            'url',
        ]


class TeamMemberSerializer(serializers.ModelSerializer):
    social_media = SocialMediaSerializer(many=True, read_only=True)

    class Meta:
        model = TeamMember
        fields = [
            'id',
            'name',
            'role',
            'initials',
            'image',
            'email',
            'social_media',
            'is_active',
            'display_order',
        ]
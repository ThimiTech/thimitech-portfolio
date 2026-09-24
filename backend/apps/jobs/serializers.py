from rest_framework import serializers

from .models import Job, Requirement


class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = [
            'id',
            'text',
            'display_order',
        ]


class JobSerializer(serializers.ModelSerializer):
    requirements = RequirementSerializer(
        many=True,
        read_only=True
    )

    class Meta:
        model = Job
        fields = [
            'id',
            'title',
            'employment_type',
            'description',
            'requirements',
            'is_active',
            'display_order',
        ]
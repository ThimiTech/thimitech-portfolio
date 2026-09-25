from rest_framework import serializers

from .models import Job, Requirement, JobApplication


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

class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = [
            'id',
            'job',
            'cover_letter',
            'cv',
            'applied_at',
        ]
        read_only_fields = ['id', 'applied_at']        
from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from .models import Job, Requirement, JobApplication

MAX_CV_BYTES = 5 * 1024 * 1024
CV_EXTENSIONS = ['pdf', 'doc', 'docx']


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
    job_title = serializers.CharField(
        source='job.title',
        read_only=True
    )
    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects.filter(is_active=True))
    cv = serializers.FileField(validators=[FileExtensionValidator(CV_EXTENSIONS)])

    def validate_cv(self, f):
        if f.size > MAX_CV_BYTES:
            raise serializers.ValidationError('CV must be 5 MB or smaller.')
        return f

    class Meta:
        model = JobApplication
        fields = [
            'id',
            'job',
            'job_title',
            'name', 
            'phone',
            'address',
            'cover_letter',
            'cv',
            'status',
            'applied_at',
        ]
        read_only_fields = [
            'id',
            'job_title',    
            'status',
            'applied_at',
        ]
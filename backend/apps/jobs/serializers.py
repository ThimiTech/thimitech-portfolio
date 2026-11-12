from django.core.validators import FileExtensionValidator
from rest_framework import serializers

from apps.org.models import Department, EmployeeProfile

from .models import Job, Requirement, JobApplication

MAX_CV_BYTES = 5 * 1024 * 1024
CV_EXTENSIONS = ['pdf', 'doc', 'docx']


class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ['id', 'text', 'display_order']


class JobSerializer(serializers.ModelSerializer):
    requirements = RequirementSerializer(many=True, read_only=True)
    # HR writes requirements as a plain ordered list; it replaces the existing ones.
    requirement_texts = serializers.ListField(
        child=serializers.CharField(max_length=500, allow_blank=True), write_only=True, required=False, max_length=30)

    class Meta:
        model = Job
        fields = ['id', 'title', 'employment_type', 'description', 'requirements', 'requirement_texts',
                  'is_active', 'display_order']

    def _set_requirements(self, job, texts):
        if texts is None:
            return
        job.requirements.all().delete()
        Requirement.objects.bulk_create(
            Requirement(job=job, text=t.strip(), display_order=i) for i, t in enumerate(texts) if t.strip())

    def create(self, validated_data):
        texts = validated_data.pop('requirement_texts', None)
        job = super().create(validated_data)
        self._set_requirements(job, texts)
        return job

    def update(self, instance, validated_data):
        texts = validated_data.pop('requirement_texts', None)
        job = super().update(instance, validated_data)
        self._set_requirements(job, texts)
        return job


class HiringJobSerializer(JobSerializer):
    """HR view of a posting: adds how many applications it has, and how many are still unreviewed."""
    application_count = serializers.IntegerField(read_only=True)
    pending_count = serializers.IntegerField(read_only=True)

    class Meta(JobSerializer.Meta):
        fields = JobSerializer.Meta.fields + ['application_count', 'pending_count']


class JobApplicationSerializer(serializers.ModelSerializer):
    """The applicant's own view: what they sent and where it stands. No internal notes."""
    job_title = serializers.CharField(source='job.title', read_only=True)
    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects.filter(is_active=True))
    cv = serializers.FileField(validators=[FileExtensionValidator(CV_EXTENSIONS)])

    def validate_cv(self, f):
        if f.size > MAX_CV_BYTES:
            raise serializers.ValidationError('CV must be 5 MB or smaller.')
        return f

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'job_title', 'name', 'phone', 'address', 'cover_letter', 'cv', 'status', 'applied_at']
        read_only_fields = ['id', 'job_title', 'status', 'applied_at']


class HiringApplicationSerializer(serializers.ModelSerializer):
    """HR view. Only `status` and `hr_notes` are writable; the CV is fetched from the `cv` action, never by URL."""
    job_title = serializers.CharField(source='job.title', read_only=True)
    email = serializers.EmailField(source='applicant.email', read_only=True)
    applicant_role = serializers.CharField(source='applicant.role', read_only=True)
    cv_name = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'job_title', 'applicant', 'applicant_role', 'name', 'email', 'phone', 'address',
                  'cover_letter', 'cv_name', 'status', 'hr_notes', 'applied_at', 'updated_at']
        read_only_fields = [f for f in fields if f not in ('status', 'hr_notes')]

    def get_cv_name(self, obj) -> str:
        return obj.cv.name.rsplit('/', 1)[-1] if obj.cv else ''


class HireSerializer(serializers.Serializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False, allow_null=True)
    designation = serializers.CharField(max_length=120, required=False, allow_blank=True)
    employment_type = serializers.ChoiceField(choices=EmployeeProfile.EmploymentType.choices, required=False)
    join_date = serializers.DateField(required=False)

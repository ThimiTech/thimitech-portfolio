import os

from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.urls import reverse
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from .access import visible_projects, require_manager, can_manage
from .models import Project, Board, Column, Task, Comment, Milestone, ProjectLink, Sprint, Document, Note, Meeting, Whiteboard

User = get_user_model()

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
MAX_COVER_BYTES = 5 * 1024 * 1024
DOCUMENT_EXTENSIONS = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'txt', 'md', 'csv', 'docx', 'xlsx', 'pptx', 'zip']


def name_of(user):
    return (user.get_full_name() or user.email) if user else None


def string_list(value, limit, length, label):
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(x, str) or not x.strip() or len(x) > length for x in value):
        raise serializers.ValidationError(f'Use up to {limit} non-empty {label}, each at most {length} characters.')
    return list(dict.fromkeys(x.strip() for x in value))


def dates_valid(attrs, instance):
    start = attrs.get('start_date', getattr(instance, 'start_date', None))
    end = attrs.get('due_date', getattr(instance, 'due_date', None))
    if start and end and end < start:
        raise serializers.ValidationError({'due_date': 'Due date must be on or after the start date.'})


@extend_schema_serializer(component_name='ProjectMember')
class PersonSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name']

    def get_name(self, user) -> str:
        return user.get_full_name() or user.email


class ColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Column
        fields = ['id', 'board', 'name', 'position', 'status']

    def validate(self, attrs):
        board = attrs.get('board', getattr(self.instance, 'board', None))
        require_manager(self.context['request'].user, board.project)
        if self.instance and board.pk != self.instance.board_id:
            raise serializers.ValidationError({'board': 'A column cannot move between boards.'})
        return attrs


class BoardSerializer(serializers.ModelSerializer):
    columns = ColumnSerializer(many=True, read_only=True)

    class Meta:
        model = Board
        fields = ['id', 'project', 'name', 'columns']

    def validate(self, attrs):
        project = attrs.get('project', getattr(self.instance, 'project', None))
        require_manager(self.context['request'].user, project)
        if self.instance and project.pk != self.instance.project_id:
            raise serializers.ValidationError({'project': 'A board cannot move between projects.'})
        return attrs


class ProgressSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    done = serializers.IntegerField()
    percent = serializers.IntegerField()


@extend_schema_serializer(component_name='WorkProject')
class ProjectSerializer(serializers.ModelSerializer):
    lead = serializers.PrimaryKeyRelatedField(read_only=True)
    members = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.filter(is_active=True).exclude(role='guest'), required=False)
    people = serializers.SerializerMethodField()
    boards = BoardSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()
    cover = serializers.ImageField(required=False, allow_null=True)
    remove_cover = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Project
        fields = ['id', 'name', 'key', 'description', 'lead', 'members', 'people', 'start_date', 'due_date', 'archived', 'health',
                  'visibility', 'slug', 'tagline', 'cover', 'remove_cover', 'story', 'tech', 'public_sections', 'published_at',
                  'created_at', 'updated_at', 'boards', 'progress', 'can_manage']
        read_only_fields = ['created_at', 'updated_at', 'published_at']

    def validate_cover(self, value):
        if value and value.size > MAX_COVER_BYTES:
            raise serializers.ValidationError('Cover image must be 5 MB or smaller.')
        return value

    def validate_tech(self, value):
        return string_list(value, 24, 40, 'technologies')

    def validate_public_sections(self, value):
        if not isinstance(value, list) or set(value) - set(Project.PUBLIC_SECTIONS):
            raise serializers.ValidationError(f'Choose from: {", ".join(Project.PUBLIC_SECTIONS)}.')
        return list(dict.fromkeys(value))

    def validate_slug(self, value):
        return value.lower() if value else None

    def update(self, instance, validated_data):
        if validated_data.pop('remove_cover', False) and 'cover' not in validated_data:
            validated_data['cover'] = None
        if 'cover' in validated_data and instance.cover:
            instance.cover.delete(save=False)  # replaced or removed: don't orphan the old file
        if validated_data.get('cover', '') is None:
            validated_data['cover'] = ''
        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data.pop('remove_cover', None)
        if validated_data.get('cover') is None:
            validated_data.pop('cover', None)
        return super().create(validated_data)

    def validate_key(self, value):
        duplicates = Project.objects.filter(key__iexact=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError('This project key is already in use.')
        return value.upper()

    def validate(self, attrs):
        dates_valid(attrs, self.instance)
        visibility = attrs.get('visibility', getattr(self.instance, 'visibility', 'private'))
        if visibility == 'public' and not attrs.get('slug', getattr(self.instance, 'slug', None)):
            raise serializers.ValidationError({'slug': 'Set a public URL slug before publishing.'})
        if self.instance and 'members' in attrs:
            ids = {user.pk for user in attrs['members']} | {self.instance.lead_id}
            if Task.objects.filter(column__board__project=self.instance, assignee__isnull=False).exclude(assignee_id__in=ids).exists():
                raise serializers.ValidationError({'members': 'Reassign tasks before removing their assignees.'})
        return attrs

    @extend_schema_field(PersonSerializer(many=True))
    def get_people(self, project):
        people = {p.pk: p for p in project.members.all()}
        people[project.lead_id] = project.lead
        return PersonSerializer(people.values(), many=True).data

    @extend_schema_field(ProgressSerializer)
    def get_progress(self, project):
        if hasattr(project, 'total_tasks'):
            total, done = project.total_tasks, project.done_tasks
        else:  # newly created objects have not been through the annotated read queryset
            tasks = Task.objects.filter(column__board__project=project)
            total, done = tasks.count(), tasks.filter(column__status='done').count()
        return {'total': total, 'done': done, 'percent': round(done / total * 100) if total else 0}

    def get_can_manage(self, project) -> bool:
        return can_manage(self.context['request'].user, project)


class TaskSerializer(serializers.ModelSerializer):
    project = serializers.IntegerField(source='column.board.project_id', read_only=True)
    board = serializers.IntegerField(source='column.board_id', read_only=True)
    status = serializers.CharField(source='column.status', read_only=True)
    assignee_name = serializers.SerializerMethodField()
    key = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'key', 'project', 'board', 'title', 'description', 'column', 'status', 'assignee', 'assignee_name', 'priority', 'estimate', 'labels', 'position', 'milestone', 'sprint', 'start_date', 'due_date', 'completed_at', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'completed_at']

    def get_key(self, task) -> str:
        return f'{task.column.board.project.key}-{task.pk}'

    def get_assignee_name(self, task) -> str | None:
        return name_of(task.assignee)

    def validate_labels(self, value):
        return string_list(value, 12, 40, 'text labels')

    def validate(self, attrs):
        column = attrs.get('column', getattr(self.instance, 'column', None))
        project = column.board.project
        if not visible_projects(self.context['request'].user).filter(pk=project.pk).exists():
            raise serializers.ValidationError({'column': 'Choose a column in an accessible project.'})
        if self.instance and column.board_id != self.instance.column.board_id:
            raise serializers.ValidationError({'column': 'Choose a column on the same board.'})
        assignee = attrs.get('assignee', getattr(self.instance, 'assignee', None))
        if assignee and (not assignee.is_active or not assignee.has_role('employee') or (assignee.pk != project.lead_id and not project.members.filter(pk=assignee.pk).exists())):
            raise serializers.ValidationError({'assignee': 'Assignee must be an active member of this project.'})
        milestone = attrs.get('milestone', getattr(self.instance, 'milestone', None))
        if milestone and milestone.project_id != project.pk:
            raise serializers.ValidationError({'milestone': 'Choose a milestone in this project.'})
        sprint = attrs.get('sprint', getattr(self.instance, 'sprint', None))
        if sprint and sprint.project_id != project.pk:
            raise serializers.ValidationError({'sprint': 'Choose a sprint in this project.'})
        if sprint and sprint.status == 'completed' and sprint.pk != getattr(self.instance, 'sprint_id', None):
            raise serializers.ValidationError({'sprint': 'This sprint is already completed.'})
        dates_valid(attrs, self.instance)
        return attrs


class ProjectChildSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        project = attrs.get('project', getattr(self.instance, 'project', None))
        require_manager(self.context['request'].user, project)
        if self.instance and project.pk != self.instance.project_id:
            raise serializers.ValidationError({'project': 'This item cannot move between projects.'})
        return attrs


class MilestoneSerializer(ProjectChildSerializer):
    class Meta:
        model = Milestone
        fields = ['id', 'project', 'title', 'due_date', 'completed']


class LinkSerializer(ProjectChildSerializer):
    class Meta:
        model = ProjectLink
        fields = ['id', 'project', 'title', 'kind', 'url', 'public']

    def validate_url(self, value):
        if not value.startswith(('https://', 'http://')):
            raise serializers.ValidationError('Use an HTTP or HTTPS URL.')
        return value


class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'task', 'author', 'author_name', 'body', 'created_at']
        read_only_fields = ['author', 'created_at']

    def get_author_name(self, comment) -> str:
        return comment.author.get_full_name() or comment.author.email

    def validate_task(self, task):
        if not visible_projects(self.context['request'].user).filter(pk=task.column.board.project_id).exists():
            raise serializers.ValidationError('Task is not accessible.')
        return task


class SprintSerializer(ProjectChildSerializer):
    class Meta:
        model = Sprint
        fields = ['id', 'project', 'name', 'goal', 'start_date', 'end_date', 'status', 'completed_at']
        read_only_fields = ['status', 'completed_at']  # changed via the start/complete actions

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'End date must be on or after the start date.'})
        return attrs


class MemberChildSerializer(serializers.ModelSerializer):
    """Collaborative project content: any project member may create; the project cannot change afterwards."""
    def validate(self, attrs):
        project = attrs.get('project', getattr(self.instance, 'project', None))
        if not visible_projects(self.context['request'].user).filter(pk=project.pk).exists():
            raise serializers.ValidationError({'project': 'Choose an accessible project.'})
        if self.instance and project.pk != self.instance.project_id:
            raise serializers.ValidationError({'project': 'This item cannot move between projects.'})
        return attrs


class DocumentSerializer(MemberChildSerializer):
    file = serializers.FileField(validators=[FileExtensionValidator(DOCUMENT_EXTENSIONS)])
    url = serializers.SerializerMethodField()
    extension = serializers.CharField(read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'project', 'title', 'folder', 'description', 'file', 'url', 'extension', 'size', 'public',
                  'uploaded_by', 'uploaded_by_name', 'can_edit', 'created_at', 'updated_at']
        read_only_fields = ['size', 'uploaded_by', 'created_at', 'updated_at']

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None and not isinstance(self.instance, list):
            fields['file'].read_only = True  # upload a new document instead of replacing bytes in place
        return fields

    def get_url(self, doc) -> str:
        return reverse('pm-document-file', args=[doc.pk])

    def get_uploaded_by_name(self, doc) -> str:
        return name_of(doc.uploaded_by)

    def get_can_edit(self, doc) -> bool:
        user = self.context['request'].user
        return doc.uploaded_by_id == user.pk or can_manage(user, doc.project)

    def to_representation(self, doc):
        data = super().to_representation(doc)
        data['file'] = os.path.basename(doc.file.name)  # never expose the /media path
        return data

    def validate_file(self, f):
        if f.size > MAX_DOCUMENT_BYTES:
            raise serializers.ValidationError('Documents must be 25 MB or smaller.')
        return f

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        if attrs.get('public') and not can_manage(self.context['request'].user, project):
            raise serializers.ValidationError({'public': 'Only the project lead can publish documents.'})
        return attrs


class NoteSerializer(MemberChildSerializer):
    author_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ['id', 'project', 'title', 'body', 'pinned', 'author', 'author_name', 'updated_by_name', 'created_at', 'updated_at']
        read_only_fields = ['author', 'created_at', 'updated_at']

    def get_author_name(self, note) -> str:
        return name_of(note.author)

    def get_updated_by_name(self, note) -> str | None:
        return name_of(note.updated_by)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        title = attrs.get('title', getattr(self.instance, 'title', ''))
        clash = Note.objects.filter(project=project, title__iexact=title.strip())
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({'title': 'A note with this title already exists in the project.'})
        return attrs


class MeetingSerializer(MemberChildSerializer):
    attendees = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.filter(is_active=True), required=False)
    attendees_detail = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Meeting
        fields = ['id', 'project', 'title', 'kind', 'start', 'end', 'location', 'agenda', 'minutes', 'action_items', 'status',
                  'attendees', 'attendees_detail', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    @extend_schema_field(PersonSerializer(many=True))
    def get_attendees_detail(self, meeting):
        return PersonSerializer(meeting.attendees.all(), many=True).data

    def get_created_by_name(self, meeting) -> str:
        return name_of(meeting.created_by)

    def validate_action_items(self, items):
        shape = {'text': str, 'assignee': (int, type(None)), 'due': (str, type(None)), 'task': (int, type(None)), 'done': bool}
        if not isinstance(items, list) or len(items) > 100:
            raise serializers.ValidationError('Use a list of at most 100 action items.')
        clean = []
        for item in items:
            if not isinstance(item, dict) or not str(item.get('text', '')).strip() or len(item['text']) > 500:
                raise serializers.ValidationError('Each action item needs text of at most 500 characters.')
            row = {'text': item['text'].strip(), 'assignee': item.get('assignee'), 'due': item.get('due') or None,
                   'task': item.get('task'), 'done': bool(item.get('done', False))}
            if any(not isinstance(row[k], t) for k, t in shape.items()):
                raise serializers.ValidationError('Action item fields have the wrong type.')
            clean.append(row)
        return clean

    def validate(self, attrs):
        attrs = super().validate(attrs)
        project = attrs.get('project', getattr(self.instance, 'project', None))
        start = attrs.get('start', getattr(self.instance, 'start', None))
        end = attrs.get('end', getattr(self.instance, 'end', None))
        if start and end and end <= start:
            raise serializers.ValidationError({'end': 'The meeting must end after it starts.'})
        team = {project.lead_id, *project.members.values_list('pk', flat=True)}
        if any(u.pk not in team for u in attrs.get('attendees', [])):
            raise serializers.ValidationError({'attendees': 'Invite members of this project.'})
        return attrs


class WhiteboardSerializer(MemberChildSerializer):
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Whiteboard
        fields = ['id', 'project', 'title', 'data', 'version', 'updated_by_name', 'created_at', 'updated_at']
        read_only_fields = ['version', 'created_at', 'updated_at']

    def get_updated_by_name(self, board) -> str | None:
        return name_of(board.updated_by)

    def validate_data(self, value):
        if not isinstance(value, dict) or not isinstance(value.get('elements', []), list) or len(value.get('elements', [])) > 5000:
            raise serializers.ValidationError('Whiteboard data must be {elements: [...]} with at most 5000 elements.')
        return value


class ProjectSummarySerializer(serializers.Serializer):
    projects = serializers.IntegerField()
    tasks = serializers.IntegerField()
    done = serializers.IntegerField()
    active = serializers.IntegerField()
    overdue = serializers.IntegerField()
    assigned_to_me = serializers.IntegerField()

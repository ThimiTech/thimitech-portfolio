from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from .access import visible_projects, require_manager
from .models import Project, Board, Column, Task, Comment, Milestone, ProjectLink

User = get_user_model()


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

    class Meta:
        model = Project
        fields = ['id', 'name', 'key', 'description', 'lead', 'members', 'people', 'start_date', 'due_date', 'archived', 'created_at', 'updated_at', 'boards', 'progress', 'can_manage']
        read_only_fields = ['created_at', 'updated_at']

    def validate_key(self, value):
        duplicates = Project.objects.filter(key__iexact=value)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError('This project key is already in use.')
        return value.upper()

    def validate(self, attrs):
        dates_valid(attrs, self.instance)
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
        from .access import can_manage
        return can_manage(self.context['request'].user, project)


class TaskSerializer(serializers.ModelSerializer):
    project = serializers.IntegerField(source='column.board.project_id', read_only=True)
    board = serializers.IntegerField(source='column.board_id', read_only=True)
    status = serializers.CharField(source='column.status', read_only=True)
    assignee_name = serializers.SerializerMethodField()
    key = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ['id', 'key', 'project', 'board', 'title', 'description', 'column', 'status', 'assignee', 'assignee_name', 'priority', 'estimate', 'labels', 'position', 'milestone', 'start_date', 'due_date', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_key(self, task) -> str:
        return f'{task.column.board.project.key}-{task.pk}'

    def get_assignee_name(self, task) -> str | None:
        return (task.assignee.get_full_name() or task.assignee.email) if task.assignee else None

    def validate_labels(self, value):
        if not isinstance(value, list) or len(value) > 12 or any(not isinstance(x, str) or not x.strip() or len(x) > 40 for x in value):
            raise serializers.ValidationError('Use up to 12 non-empty text labels, each at most 40 characters.')
        return list(dict.fromkeys(x.strip() for x in value))

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
        fields = ['id', 'project', 'title', 'kind', 'url']

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


class ProjectSummarySerializer(serializers.Serializer):
    projects = serializers.IntegerField()
    tasks = serializers.IntegerField()
    done = serializers.IntegerField()
    active = serializers.IntegerField()
    overdue = serializers.IntegerField()
    assigned_to_me = serializers.IntegerField()

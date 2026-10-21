from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.notifications.services import push
from apps.permissions.permissions import IsEmployee, IsManager
from .access import visible_projects, can_manage, require_manager
from .models import Project, Board, Column, Task, Comment, Milestone, ProjectLink
from .serializers import ProjectSerializer, BoardSerializer, ColumnSerializer, TaskSerializer, CommentSerializer, MilestoneSerializer, LinkSerializer, ProjectSummarySerializer


@extend_schema(tags=['Project management'])
class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer

    def get_permissions(self):
        return [IsManager()] if self.action == 'create' else [IsEmployee()]

    def get_queryset(self):
        return visible_projects(self.request.user).select_related('lead').prefetch_related('members', 'boards__columns').annotate(
            total_tasks=Count('boards__columns__tasks', distinct=True),
            done_tasks=Count('boards__columns__tasks', filter=Q(boards__columns__status='done'), distinct=True),
        )

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.save(lead=self.request.user)
        project.members.add(self.request.user)
        create_board(project, 'Main board')

    @transaction.atomic
    def perform_update(self, serializer):
        require_manager(self.request.user, serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        require_manager(self.request.user, instance)
        raise ValidationError('Archive projects to preserve their task history.')


def create_board(project, name):
    board = Board.objects.create(project=project, name=name)
    for index, (status, label) in enumerate(Column.Status.choices):
        Column.objects.create(board=board, name=label, status=status, position=index)
    return board


class ScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsEmployee]
    project_path = 'project'

    def get_queryset(self):
        queryset = self.queryset.filter(**{f'{self.project_path}__in': visible_projects(self.request.user)})
        project = self.request.query_params.get('project')
        if project:
            if not project.isdigit():
                raise ValidationError({'project': 'Use a project id.'})
            queryset = queryset.filter(**{f'{self.project_path}_id': project})
        return queryset

    def project_of(self, instance):
        for attr in self.project_path.split('__'):
            instance = getattr(instance, attr)
        return instance

    def perform_destroy(self, instance):
        require_manager(self.request.user, self.project_of(instance))
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError('Move the tasks out before deleting this column or board.')


@extend_schema(tags=['Project management'])
class BoardViewSet(ScopedViewSet):
    queryset = Board.objects.select_related('project').prefetch_related('columns')
    serializer_class = BoardSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        serializer.instance = create_board(project, serializer.validated_data['name'])


@extend_schema(tags=['Project management'])
class ColumnViewSet(ScopedViewSet):
    queryset = Column.objects.select_related('board__project')
    serializer_class = ColumnSerializer
    project_path = 'board__project'


@extend_schema(tags=['Project management'])
class TaskViewSet(ScopedViewSet):
    queryset = Task.objects.select_related('column__board__project', 'assignee', 'milestone')
    serializer_class = TaskSerializer
    project_path = 'column__board__project'

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get('mine') == '1':
            qs = qs.filter(assignee=self.request.user)
        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data['column'].board.project
        require_manager(self.request.user, project)
        notify_assignee(serializer.save(created_by=self.request.user), None, self.request.user)

    def perform_update(self, serializer):
        before = serializer.instance.assignee_id
        notify_assignee(serializer.save(), before, self.request.user)

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        if not can_manage(request.user, self.project_of(task)):
            if task.assignee_id != request.user.pk or set(request.data) - {'column', 'position'}:
                raise PermissionDenied('Employees can move only their assigned tasks. Ask the project lead to edit task details.')
        return super().update(request, *args, **kwargs)


def notify_assignee(task, previous_assignee_id, actor):
    """In-app notice to a task's new assignee (not when you assign yourself)."""
    if task.assignee_id and task.assignee_id != previous_assignee_id:
        project = task.column.board.project
        push([task.assignee], 'task_assigned', f'{actor.full_name} assigned you {project.key}-{task.pk}',
             task.title, f'/app/projects/{project.pk}', exclude=actor)


@extend_schema(tags=['Project management'])
class MilestoneViewSet(ScopedViewSet):
    queryset = Milestone.objects.select_related('project')
    serializer_class = MilestoneSerializer


@extend_schema(tags=['Project management'])
class LinkViewSet(ScopedViewSet):
    queryset = ProjectLink.objects.select_related('project')
    serializer_class = LinkSerializer


@extend_schema(tags=['Project management'])
class CommentViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsEmployee]

    def get_queryset(self):
        qs = Comment.objects.filter(task__column__board__project__in=visible_projects(self.request.user)).select_related('author', 'task__column__board__project')
        task = self.request.query_params.get('task')
        if task:
            if not task.isdigit():
                raise ValidationError({'task': 'Use a task id.'})
            qs = qs.filter(task_id=task)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_destroy(self, instance):
        if instance.author_id != self.request.user.pk:
            require_manager(self.request.user, instance.task.column.board.project)
        instance.delete()


@extend_schema(tags=['Project management'])
class SummaryView(APIView):
    permission_classes = [IsEmployee]

    @extend_schema(responses=ProjectSummarySerializer)
    def get(self, request):
        projects = visible_projects(request.user).filter(archived=False)
        tasks = Task.objects.filter(column__board__project__in=projects)
        counts = tasks.aggregate(tasks=Count('id'), done=Count('id', filter=Q(column__status='done')), active=Count('id', filter=Q(column__status='active')), overdue=Count('id', filter=Q(due_date__lt=timezone.localdate()) & ~Q(column__status='done')))
        return Response({'projects': projects.count(), **counts, 'assigned_to_me': tasks.filter(assignee=request.user).exclude(column__status='done').count()})

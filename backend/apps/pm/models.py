import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def private_path(instance, filename):
    # Unguessable dir; documents are served only through the scoped API (/api/pm/documents/{id}/file/).
    return f'pm/docs/{uuid.uuid4().hex}/{os.path.basename(filename)}'


def cover_path(instance, filename):
    return f'pm/covers/{uuid.uuid4().hex}/{os.path.basename(filename)}'


class Project(models.Model):
    PUBLIC_SECTIONS = ['story', 'progress', 'milestones', 'team', 'links', 'gallery', 'documents']

    name = models.CharField(max_length=200)
    key = models.SlugField(max_length=12, unique=True)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='led_projects')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='work_projects', blank=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    health = models.CharField(max_length=10, choices=[('on_track', 'On track'), ('at_risk', 'At risk'), ('off_track', 'Off track')], default='on_track')
    # public profile (case study at /work/<slug>); only `public_sections` leave the building
    visibility = models.CharField(max_length=8, choices=[('private', 'Private'), ('public', 'Public')], default='private')
    slug = models.SlugField(max_length=80, unique=True, null=True, blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    cover = models.ImageField(upload_to=cover_path, blank=True)
    story = models.TextField(blank=True)  # markdown
    tech = models.JSONField(default=list, blank=True)
    public_sections = models.JSONField(default=list, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Board(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='boards')
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['id']


class Column(models.Model):
    class Status(models.TextChoices):
        BACKLOG = 'backlog', 'Backlog'
        ACTIVE = 'active', 'In progress'
        REVIEW = 'review', 'In review'
        DONE = 'done', 'Done'

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=80)
    position = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.BACKLOG)

    class Meta:
        ordering = ['position', 'id']


class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones')
    title = models.CharField(max_length=200)
    due_date = models.DateField()
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['due_date', 'id']


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    column = models.ForeignKey(Column, on_delete=models.PROTECT, related_name='tasks')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='project_tasks')
    milestone = models.ForeignKey(Milestone, null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    sprint = models.ForeignKey('Sprint', null=True, blank=True, on_delete=models.SET_NULL, related_name='tasks')
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')], default='medium')
    estimate = models.PositiveSmallIntegerField(null=True, blank=True)
    labels = models.JSONField(default=list, blank=True)
    position = models.PositiveIntegerField(default=0)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_tasks')
    completed_at = models.DateTimeField(null=True, blank=True, editable=False)  # feeds sprint burndown
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', 'id']

    def save(self, *args, **kwargs):
        done = self.column.status == Column.Status.DONE
        if done and not self.completed_at:
            self.completed_at = timezone.now()
        elif not done:
            self.completed_at = None
        if kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = {*kwargs['update_fields'], 'completed_at'}
        super().save(*args, **kwargs)


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=10000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class ProjectLink(models.Model):
    KINDS = [('github', 'GitHub'), ('gitlab', 'GitLab'), ('web', 'Website'), ('youtube', 'YouTube'), ('docs', 'Documentation'),
             ('figma', 'Figma'), ('drive', 'Drive'), ('linkedin', 'LinkedIn'), ('facebook', 'Facebook'),
             ('instagram', 'Instagram'), ('x', 'X / Twitter'), ('discord', 'Discord'), ('slack', 'Slack'),
             ('store', 'App store'), ('other', 'Other')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='links')
    title = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=KINDS, default='web')
    url = models.URLField(max_length=1000)
    public = models.BooleanField(default=False)

    class Meta:
        ordering = ['id']


class Sprint(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sprints')
    name = models.CharField(max_length=120)
    goal = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=[('planned', 'Planned'), ('active', 'Active'), ('completed', 'Completed')], default='planned')
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['start_date', 'id']
        constraints = [models.UniqueConstraint(fields=['project'], condition=models.Q(status='active'), name='one_active_sprint_per_project')]


class Document(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=200)
    folder = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=private_path)
    size = models.PositiveIntegerField(default=0, editable=False)
    public = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pm_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['folder', 'title', 'id']

    @property
    def extension(self):
        return os.path.splitext(self.file.name)[1].lower().lstrip('.')


class Note(models.Model):
    """Markdown note; [[Title]] wikilinks between notes/docs/tasks form the knowledge graph (resolved client-side)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, max_length=200_000)
    pinned = models.BooleanField(default=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pm_notes')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-pinned', 'title', 'id']
        constraints = [models.UniqueConstraint(Lower('title'), 'project', name='unique_note_title_per_project')]


class Meeting(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='meetings')
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=12, choices=[('standup', 'Stand-up'), ('planning', 'Sprint planning'), ('review', 'Sprint review'),
                                                    ('retro', 'Retrospective'), ('client', 'Client'), ('general', 'General')], default='general')
    start = models.DateTimeField()
    end = models.DateTimeField()
    location = models.CharField(max_length=300, blank=True)  # room or call URL
    agenda = models.TextField(blank=True)  # markdown
    minutes = models.TextField(blank=True)  # markdown
    action_items = models.JSONField(default=list, blank=True)  # [{text, assignee, due, task, done}]
    status = models.CharField(max_length=10, choices=[('scheduled', 'Scheduled'), ('done', 'Held'), ('cancelled', 'Cancelled')], default='scheduled')
    attendees = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='pm_meetings', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start', 'id']


class Whiteboard(models.Model):
    """Freeform canvas; `data` = {elements: [...]}. `version` guards concurrent saves (stale write -> 409)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='whiteboards')
    title = models.CharField(max_length=120)
    data = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', 'id']

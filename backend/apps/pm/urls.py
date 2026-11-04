from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (ProjectViewSet, BoardViewSet, ColumnViewSet, TaskViewSet, CommentViewSet, MilestoneViewSet, LinkViewSet,
                    SummaryView, SprintViewSet, DocumentViewSet, NoteViewSet, MeetingViewSet, WhiteboardViewSet, PublicProjectViewSet)

router = DefaultRouter()
router.register('projects', ProjectViewSet, basename='pm-project')
router.register('boards', BoardViewSet, basename='pm-board')
router.register('columns', ColumnViewSet, basename='pm-column')
router.register('tasks', TaskViewSet, basename='pm-task')
router.register('comments', CommentViewSet, basename='pm-comment')
router.register('milestones', MilestoneViewSet, basename='pm-milestone')
router.register('links', LinkViewSet, basename='pm-link')
router.register('sprints', SprintViewSet, basename='pm-sprint')
router.register('documents', DocumentViewSet, basename='pm-document')
router.register('notes', NoteViewSet, basename='pm-note')
router.register('meetings', MeetingViewSet, basename='pm-meeting')
router.register('whiteboards', WhiteboardViewSet, basename='pm-whiteboard')
router.register('public', PublicProjectViewSet, basename='pm-public')
urlpatterns = [path('summary/', SummaryView.as_view())] + router.urls

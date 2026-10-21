from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, BoardViewSet, ColumnViewSet, TaskViewSet, CommentViewSet, MilestoneViewSet, LinkViewSet, SummaryView

router = DefaultRouter()
router.register('projects', ProjectViewSet, basename='pm-project')
router.register('boards', BoardViewSet, basename='pm-board')
router.register('columns', ColumnViewSet, basename='pm-column')
router.register('tasks', TaskViewSet, basename='pm-task')
router.register('comments', CommentViewSet, basename='pm-comment')
router.register('milestones', MilestoneViewSet, basename='pm-milestone')
router.register('links', LinkViewSet, basename='pm-link')
urlpatterns = [path('summary/', SummaryView.as_view())] + router.urls

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CalendarEventViewSet, FeedView, HolidayViewSet

router = DefaultRouter()
router.register('holidays', HolidayViewSet, basename='holiday')
router.register('events', CalendarEventViewSet, basename='calendar-event')

urlpatterns = [path('feed/', FeedView.as_view(), name='calendar-feed')] + router.urls

from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AuditViewSet, OptionsView
router = DefaultRouter()
router.register('events', AuditViewSet, basename='audit-event')
urlpatterns = [path('options/', OptionsView.as_view())] + router.urls

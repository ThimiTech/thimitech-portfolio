from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import MyAssignmentViewSet, CategoryViewSet, AssetViewSet, AssignmentViewSet, SummaryView
router = DefaultRouter()
router.register('my-assets', MyAssignmentViewSet, basename='inventory-my-asset')
router.register('categories', CategoryViewSet, basename='inventory-category')
router.register('assets', AssetViewSet, basename='inventory-asset')
router.register('assignments', AssignmentViewSet, basename='inventory-assignment')
urlpatterns = [path('summary/', SummaryView.as_view())] + router.urls

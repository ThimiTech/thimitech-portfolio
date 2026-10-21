from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, OrganizationViewSet, PersonViewSet, StructureView

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='org-department')
router.register('people', PersonViewSet, basename='org-person')

urlpatterns = [
    path('organization/', OrganizationViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
         name='org-organization'),
    path('structure/', StructureView.as_view(), name='org-structure'),
] + router.urls

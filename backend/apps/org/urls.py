from django.urls import path
from rest_framework.routers import DefaultRouter

from .onboarding import StepViewSet, TaskViewSet
from .views import DepartmentViewSet, OrganizationViewSet, PersonViewSet, PublicOrganizationView, StructureView

router = DefaultRouter()
router.register('departments', DepartmentViewSet, basename='org-department')
router.register('people', PersonViewSet, basename='org-person')
router.register('onboarding/steps', StepViewSet, basename='org-onboarding-step')
router.register('onboarding/tasks', TaskViewSet, basename='org-onboarding-task')

urlpatterns = [
    path('organization/', OrganizationViewSet.as_view({'get': 'retrieve', 'patch': 'partial_update'}),
         name='org-organization'),
    path('public/', PublicOrganizationView.as_view(), name='org-public'),
    path('structure/', StructureView.as_view(), name='org-structure'),
] + router.urls

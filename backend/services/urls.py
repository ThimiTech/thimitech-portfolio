from django.urls import path
from .views import service_list, project_list

urlpatterns = [
    path('services/', service_list, name='service-list'),
    path('projects/', project_list, name='project-list')
]
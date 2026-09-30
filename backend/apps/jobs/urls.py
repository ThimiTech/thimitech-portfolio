from django.urls import path
from .views import job_list, apply_for_job

urlpatterns = [
    path('jobs/', job_list, name='job-list'),
    path('jobs/apply/', apply_for_job, name='apply-for-job'),
    ]
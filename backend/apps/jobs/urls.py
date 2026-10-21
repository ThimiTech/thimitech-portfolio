from django.urls import path
from .views import job_list, job_detail, apply_for_job, my_applications

urlpatterns = [
    path('jobs/', job_list, name='job-list'),
    path('jobs/<int:pk>/', job_detail, name='job-detail'),
    path('jobs/apply/', apply_for_job, name='apply-for-job'),
    path('jobs/applications/', my_applications, name='my-applications'),
    ]
from django.urls import path
from .views import service_list

urlpatterns = [
    path('services/', service_list, name='service-list'),
 
]
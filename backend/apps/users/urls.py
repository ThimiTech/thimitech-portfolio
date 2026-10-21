from django.urls import path
from .views import register, me, password_reset, password_reset_confirm

urlpatterns = [
    path('register/', register, name='register'),
    path('me/', me, name='me'),
    path('password-reset/', password_reset, name='password-reset'),
    path('password-reset/confirm/', password_reset_confirm, name='password-reset-confirm'),
]

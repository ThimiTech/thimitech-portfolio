"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.utils import extend_schema

from django.conf import settings
from django.conf.urls.static import static

from apps.org.dashboard import DashboardView, NavCountsView
from apps.audit.views import MonitoringView

from apps.users.throttles import LoginIPThrottle, LoginThrottle, TokenRefreshThrottle


@extend_schema(tags=['Authentication'])
class CustomTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [LoginThrottle, LoginIPThrottle]


@extend_schema(tags=['Authentication'])
class CustomTokenRefreshView(TokenRefreshView):
    throttle_classes = [TokenRefreshThrottle]


@extend_schema(tags=['Authentication'], summary='Log out: blacklist the given refresh token')
class LogoutView(TokenBlacklistView):
    pass

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/', include('apps.projects.urls')),
    path('api/', include('apps.services.urls')),
    path('api/', include('apps.users.urls')),
    path('api/', include('apps.team.urls')),
    path('api/', include('apps.jobs.urls')),
    path('api/org/', include('apps.org.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
    path('api/leave/', include('apps.leave.urls')),
    path('api/calendar/', include('apps.calendar_app.urls')),
    path('api/notices/', include('apps.notices.urls')),
    path('api/pm/', include('apps.pm.urls')),
    path('api/finance/', include('apps.finance.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/monitoring/overview/', MonitoringView.as_view(), name='monitoring-overview'),
    path('api/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('api/nav-counts/', NavCountsView.as_view(), name='nav-counts'),
    path('api/notifications/', include('apps.notifications.urls')),

    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/blacklist/', LogoutView.as_view(), name='token_blacklist'),
    
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)

from rest_framework.routers import DefaultRouter

from .views import HiringApplicationViewSet, JobViewSet

# Public URLs are unchanged: jobs/, jobs/{id}/, jobs/apply/, jobs/applications/.
router = DefaultRouter()
router.register('jobs', JobViewSet, basename='job')
router.register('hiring/applications', HiringApplicationViewSet, basename='hiring-application')
urlpatterns = router.urls

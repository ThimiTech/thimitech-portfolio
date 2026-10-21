from rest_framework.routers import DefaultRouter

from .views import AttendanceCorrectionViewSet, AttendanceRecordViewSet, AttendanceViewSet

router = DefaultRouter()
router.register('corrections', AttendanceCorrectionViewSet, basename='attendance-correction')
router.register('records', AttendanceRecordViewSet, basename='attendance-record')
router.register('', AttendanceViewSet, basename='attendance')

urlpatterns = router.urls

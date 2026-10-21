from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('types', views.LeaveTypeViewSet, basename='leave-type')
router.register('requests', views.LeaveRequestViewSet, basename='leave-request')
router.register('balances', views.LeaveBalanceViewSet, basename='leave-balance')
router.register('approvals', views.LeaveApprovalViewSet, basename='leave-approval')
router.register('calendar', views.LeaveCalendarViewSet, basename='leave-calendar')

urlpatterns = router.urls

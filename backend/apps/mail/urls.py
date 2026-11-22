from rest_framework.routers import SimpleRouter

from .views import MailViewSet, MessageViewSet

router = SimpleRouter()
router.register('messages', MessageViewSet, basename='mail-message')
router.register('', MailViewSet, basename='mail')
urlpatterns = router.urls

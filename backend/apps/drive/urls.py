from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BrowseView, FileViewSet, FolderViewSet, SharedView, ShareLinkViewSet, SpacesView

router = DefaultRouter()
router.register('folders', FolderViewSet, basename='drive-folder')
router.register('files', FileViewSet, basename='drive-file')
router.register('share-links', ShareLinkViewSet, basename='drive-share-link')
urlpatterns = [
    path('spaces/', SpacesView.as_view()),
    path('browse/', BrowseView.as_view()),
    path('shared/<str:token>/', SharedView.as_view()),
    path('shared/<str:token>/zip/', SharedView.as_view(), {'as_zip': True}),
    path('shared/<str:token>/files/<int:file_id>/', SharedView.as_view()),
] + router.urls

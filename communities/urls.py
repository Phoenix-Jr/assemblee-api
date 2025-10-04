# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CommunityViewSet, EventViewSet, MeditationViewSet, TestimonyViewSet
)

router = DefaultRouter()
router.register(r'communities', CommunityViewSet, basename='community')
router.register(r'events', EventViewSet, basename='event')
router.register(r'meditations', MeditationViewSet, basename='meditation')
router.register(r'testimonies', TestimonyViewSet, basename='testimony')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
]
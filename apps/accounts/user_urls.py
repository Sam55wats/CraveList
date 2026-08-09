from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PublicUserViewSet


router = DefaultRouter()
router.register("users", PublicUserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
]

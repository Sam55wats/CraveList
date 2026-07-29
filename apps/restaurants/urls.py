from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    FollowViewSet,
    RestaurantViewSet,
    UserRestaurantPhotoViewSet,
    UserRestaurantViewSet,
)

router = DefaultRouter()
router.register("restaurants", RestaurantViewSet, basename="restaurant")
router.register("my-restaurants", UserRestaurantViewSet, basename="my-restaurant")
router.register(
    "my-restaurant-photos",
    UserRestaurantPhotoViewSet,
    basename="my-restaurant-photo",
)
router.register("follows", FollowViewSet, basename="follow")

urlpatterns = [
    path("", include(router.urls)),
]

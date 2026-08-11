from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ExternalRestaurantViewSet,
    FeedViewSet,
    FollowViewSet,
    RecommendationViewSet,
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
router.register("feed", FeedViewSet, basename="feed")
router.register("recommendations", RecommendationViewSet, basename="recommendation")
router.register(
    "external-restaurants",
    ExternalRestaurantViewSet,
    basename="external-restaurant",
)

urlpatterns = [
    path("", include(router.urls)),
]

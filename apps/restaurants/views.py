from rest_framework import permissions, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Follow, UserRestaurant
from .serializers import FollowSerializer, RestaurantSerializer, UserRestaurantSerializer
from .services.locations import suggest_locations
from .services.search import search_restaurants


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        return search_restaurants(self.request.query_params)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        queryset = search_restaurants(request.query_params)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="location-suggestions")
    def location_suggestions(self, request):
        suggestions = suggest_locations(request.query_params.get("q"))
        return Response(suggestions)


class UserRestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = UserRestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = UserRestaurant.objects.filter(user=self.request.user)
        query_params = self.request.query_params

        bookmarked = query_params.get("bookmarked")
        visited = query_params.get("visited")
        cuisine = query_params.get("cuisine")
        city = query_params.get("city")
        price_level = query_params.get("price_level")

        if bookmarked is not None:
            queryset = queryset.filter(bookmarked=bookmarked.lower() == "true")

        if visited is not None:
            queryset = queryset.filter(visited=visited.lower() == "true")

        if cuisine:
            queryset = queryset.filter(restaurant__cuisine__iexact=cuisine)

        if city:
            queryset = queryset.filter(restaurant__city__iexact=city)

        if price_level:
            queryset = queryset.filter(restaurant__price_level=price_level)

        return queryset.select_related("restaurant", "user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FollowViewSet(viewsets.ModelViewSet):
    serializer_class = FollowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user).select_related(
            "follower",
            "following",
        )

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

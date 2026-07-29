from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Follow, UserRestaurant, UserRestaurantPhoto
from .pagination import RestaurantPagination
from .serializers import (
    FollowSerializer,
    RestaurantSerializer,
    UserRestaurantPhotoSerializer,
    UserRestaurantSerializer,
)
from .services.locations import suggest_locations
from .services.search import search_restaurants


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


class RestaurantViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RestaurantSerializer
    pagination_class = RestaurantPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = [
        "name",
        "cuisine",
        "price_level",
        "city",
        "state",
        "created_at",
        "updated_at",
    ]
    ordering = ["name"]

    def get_queryset(self):
        return search_restaurants(self.request.query_params)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        queryset = self.filter_queryset(search_restaurants(request.query_params))
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant = serializer.validated_data["restaurant"]
        existing_entry = UserRestaurant.objects.filter(
            user=request.user,
            restaurant=restaurant,
        ).first()

        if existing_entry is not None:
            data = request.data.copy()
            visit_fields = {"visited", "rating", "notes", "visited_at"}

            if "bookmarked" not in data and visit_fields.isdisjoint(data):
                data["bookmarked"] = True

            serializer = self.get_serializer(existing_entry, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserRestaurantPhotoViewSet(viewsets.ModelViewSet):
    serializer_class = UserRestaurantPhotoSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        queryset = UserRestaurantPhoto.objects.select_related(
            "user_restaurant__restaurant",
            "user_restaurant__user",
        )
        query_params = self.request.query_params

        restaurant_id = query_params.get("restaurant_id")
        user_restaurant_id = query_params.get("user_restaurant_id")

        if restaurant_id:
            queryset = queryset.filter(user_restaurant__restaurant_id=restaurant_id)

        if user_restaurant_id:
            queryset = queryset.filter(user_restaurant_id=user_restaurant_id)

        return queryset

    def perform_destroy(self, instance):
        if instance.user_restaurant.user != self.request.user:
            self.permission_denied(
                self.request,
                message="You can only delete your own photos.",
            )
        instance.delete()


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

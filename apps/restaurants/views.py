from django.db.models import Prefetch
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Follow, Restaurant, UserRestaurant, UserRestaurantPhoto
from .docs import API_ENDPOINTS
from .pagination import RestaurantPagination
from .serializers import (
    ExternalRestaurantImportAndSaveSerializer,
    ExternalRestaurantImportSerializer,
    FollowSerializer,
    PublicUserRestaurantSerializer,
    RestaurantSerializer,
    UserRestaurantPhotoSerializer,
    UserRestaurantSerializer,
)
from .services.locations import suggest_locations
from .services.providers import get_restaurant_provider
from .services.recommendations import recommend_restaurants
from .services.search import search_restaurants
from .services.filters import filter_user_restaurants


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


@api_view(["GET"])
def api_docs(request):
    return Response(
        {
            "name": "CraveList API",
            "description": "Backend endpoints currently available to the future React frontend.",
            "endpoints": API_ENDPOINTS,
        }
    )


class CurrentUserEntryMixin:
    def add_current_user_entries(self, queryset):
        user = self.request.user

        if not user.is_authenticated:
            return queryset

        return queryset.prefetch_related(
            Prefetch(
                "user_entries",
                queryset=UserRestaurant.objects.filter(user=user).only(
                    "id",
                    "user_id",
                    "restaurant_id",
                    "bookmarked",
                    "visited",
                    "rating",
                    "notes",
                    "visited_at",
                    "updated_at",
                ),
                to_attr="current_user_entries",
            )
        )


class RestaurantViewSet(CurrentUserEntryMixin, viewsets.ReadOnlyModelViewSet):
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
        return self.add_current_user_entries(
            search_restaurants(self.request.query_params)
        )

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        queryset = self.filter_queryset(
            self.add_current_user_entries(search_restaurants(request.query_params))
        )
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


class RecommendationViewSet(CurrentUserEntryMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = RestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]
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
        return self.add_current_user_entries(
            recommend_restaurants(self.request.user, self.request.query_params)
        )


class ExternalRestaurantViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action == "search":
            return [permissions.AllowAny()]

        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        source = request.query_params.get("source", "seed")
        provider = get_restaurant_provider(source)

        if provider is None:
            return Response(
                {"source": "Unsupported restaurant provider."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        restaurants = [
            restaurant.to_response_data()
            for restaurant in provider.search(request.query_params)
        ]
        return Response(restaurants)

    @action(detail=False, methods=["post"], url_path="import")
    def import_restaurant(self, request):
        serializer = ExternalRestaurantImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        restaurant, created, error_response = self.import_from_provider(
            serializer.validated_data["external_source"],
            serializer.validated_data["external_place_id"],
        )

        if error_response is not None:
            return error_response

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        response_serializer = RestaurantSerializer(
            restaurant,
            context={"request": request},
        )
        return Response(response_serializer.data, status=response_status)

    @action(detail=False, methods=["post"], url_path="import-and-save")
    def import_and_save(self, request):
        serializer = ExternalRestaurantImportAndSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        restaurant, restaurant_created, error_response = self.import_from_provider(
            validated_data["external_source"],
            validated_data["external_place_id"],
        )

        if error_response is not None:
            return error_response

        user_entry, entry_created = UserRestaurant.objects.get_or_create(
            user=request.user,
            restaurant=restaurant,
        )
        entry_data = {
            "restaurant_id": restaurant.id,
        }

        if "bookmarked" in request.data or not user_entry.visited:
            entry_data["bookmarked"] = validated_data["bookmarked"]

        if "visited" in request.data:
            entry_data["visited"] = validated_data["visited"]

        for optional_field in ("rating", "notes", "visited_at"):
            if optional_field in validated_data:
                entry_data[optional_field] = validated_data[optional_field]

        entry_serializer = UserRestaurantSerializer(
            user_entry,
            data=entry_data,
            partial=True,
            context={"request": request},
        )
        entry_serializer.is_valid(raise_exception=True)
        entry_serializer.save(user=request.user)

        response_status = (
            status.HTTP_201_CREATED
            if restaurant_created or entry_created
            else status.HTTP_200_OK
        )
        response_serializer = RestaurantSerializer(
            restaurant,
            context={"request": request},
        )
        return Response(response_serializer.data, status=response_status)

    def import_from_provider(self, external_source, external_place_id):
        provider = get_restaurant_provider(external_source)

        if provider is None:
            return (
                None,
                False,
                Response(
                    {"external_source": "Unsupported restaurant provider."},
                    status=status.HTTP_400_BAD_REQUEST,
                ),
            )

        provider_restaurant = provider.get(external_place_id)

        if provider_restaurant is None:
            return (
                None,
                False,
                Response(
                    {"external_place_id": "Restaurant was not found by this provider."},
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )

        restaurant, created = Restaurant.objects.update_or_create(
            external_source=external_source,
            external_place_id=external_place_id,
            defaults=provider_restaurant.to_restaurant_defaults(),
        )
        return restaurant, created, None


class UserRestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = UserRestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RestaurantPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = [
        "created_at",
        "updated_at",
        "visited_at",
        "rating",
        "restaurant__name",
        "restaurant__cuisine",
        "restaurant__city",
        "restaurant__price_level",
    ]
    ordering = ["-updated_at"]

    def get_queryset(self):
        queryset = UserRestaurant.objects.filter(user=self.request.user)
        queryset = filter_user_restaurants(queryset, self.request.query_params)
        return queryset.select_related("restaurant", "user").prefetch_related("photos")

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
    pagination_class = RestaurantPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
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
        user_id = query_params.get("user_id")
        username = query_params.get("username")

        if restaurant_id:
            queryset = queryset.filter(user_restaurant__restaurant_id=restaurant_id)

        if user_restaurant_id:
            queryset = queryset.filter(user_restaurant_id=user_restaurant_id)

        if user_id:
            queryset = queryset.filter(user_restaurant__user_id=user_id)

        if username:
            queryset = queryset.filter(user_restaurant__user__username__iexact=username)

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
    pagination_class = RestaurantPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Follow.objects.filter(follower=self.request.user).select_related(
            "follower",
            "following",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        following = serializer.validated_data["following"]
        existing_follow = Follow.objects.filter(
            follower=request.user,
            following=following,
        ).first()

        if existing_follow is not None:
            serializer = self.get_serializer(existing_follow)
            return Response(serializer.data, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

    @action(detail=False, methods=["get"], url_path="followers")
    def followers(self, request):
        queryset = Follow.objects.filter(following=request.user).select_related(
            "follower",
            "following",
        )
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="following")
    def following(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class FeedViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicUserRestaurantSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RestaurantPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["created_at", "updated_at", "visited_at", "rating"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        followed_user_ids = Follow.objects.filter(
            follower=self.request.user,
        ).values("following_id")

        queryset = (
            UserRestaurant.objects.filter(
                user_id__in=followed_user_ids,
                visited=True,
                rating__isnull=False,
            )
            .select_related("restaurant", "user")
            .order_by("-updated_at")
        )
        return filter_user_restaurants(queryset, self.request.query_params)

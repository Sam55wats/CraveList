from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Exists, OuterRef, Q, Subquery
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.decorators import action
from rest_framework.response import Response

from restaurants.models import Follow, UserRestaurant
from restaurants.pagination import RestaurantPagination
from restaurants.serializers import PublicUserRestaurantSerializer

from .serializers import PublicUserSerializer, RegisterSerializer, UserSerializer


User = get_user_model()


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    login(request, user)
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {"detail": "Invalid username or password."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    login(request, user)
    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({"detail": "Logged out."})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


class PublicUserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicUserSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = RestaurantPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username"]
    ordering_fields = ["username", "date_joined"]
    ordering = ["username"]

    def get_queryset(self):
        queryset = User.objects.annotate(
            followers_count=Count("follower_relationships", distinct=True),
            following_count=Count("following_relationships", distinct=True),
            visited_count=Count(
                "restaurant_entries",
                filter=Q(restaurant_entries__visited=True),
                distinct=True,
            ),
            bookmarked_count=Count(
                "restaurant_entries",
                filter=Q(restaurant_entries__bookmarked=True),
                distinct=True,
            ),
            average_rating=Avg("restaurant_entries__rating"),
        )
        user = self.request.user

        if user.is_authenticated:
            follow_queryset = Follow.objects.filter(
                follower=user,
                following=OuterRef("pk"),
            )
            queryset = queryset.annotate(
                is_following=Exists(follow_queryset),
                follow_id=Subquery(follow_queryset.values("id")[:1]),
            )

        return queryset

    @action(detail=True, methods=["get"], url_path="restaurants")
    def restaurants(self, request, pk=None):
        profile_user = self.get_object()
        queryset = (
            UserRestaurant.objects.filter(
                user=profile_user,
                visited=True,
                rating__isnull=False,
            )
            .select_related("restaurant", "user")
            .order_by("-updated_at")
        )
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = PublicUserRestaurantSerializer(
                page,
                many=True,
                context={"request": request},
            )
            return self.get_paginated_response(serializer.data)

        serializer = PublicUserRestaurantSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

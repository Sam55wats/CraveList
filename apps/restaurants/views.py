from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Follow, Restaurant, UserRestaurant
from .serializers import FollowSerializer, RestaurantSerializer, UserRestaurantSerializer


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        queryset = Restaurant.objects.all()
        query_params = self.request.query_params

        search = query_params.get("search") or query_params.get("q")
        cuisine = query_params.get("cuisine")
        address = query_params.get("address")
        city = query_params.get("city")
        state = query_params.get("state")
        country = query_params.get("country")
        price_level = query_params.get("price_level")
        external_source = query_params.get("external_source")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(cuisine__icontains=search)
                | Q(address__icontains=search)
                | Q(city__icontains=search)
                | Q(state__icontains=search)
                | Q(country__icontains=search)
            )

        if cuisine:
            queryset = queryset.filter(cuisine__icontains=cuisine)

        if address:
            queryset = queryset.filter(address__icontains=address)

        if city:
            queryset = queryset.filter(city__iexact=city)

        if state:
            queryset = queryset.filter(state__iexact=state)

        if country:
            queryset = queryset.filter(country__iexact=country)

        if price_level:
            queryset = queryset.filter(price_level=price_level)

        if external_source:
            queryset = queryset.filter(external_source__iexact=external_source)

        return queryset


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

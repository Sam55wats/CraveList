from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Restaurant
from .serializers import RestaurantSerializer


@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


class RestaurantViewSet(viewsets.ModelViewSet):
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        queryset = Restaurant.objects.all()
        query_params = self.request.query_params

        visited = query_params.get("visited")
        cuisine = query_params.get("cuisine")
        city = query_params.get("city")
        price_level = query_params.get("price_level")

        if visited is not None:
            queryset = queryset.filter(visited=visited.lower() == "true")

        if cuisine:
            queryset = queryset.filter(cuisine__iexact=cuisine)

        if city:
            queryset = queryset.filter(city__iexact=city)

        if price_level:
            queryset = queryset.filter(price_level=price_level)

        return queryset

from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Restaurant
from .serializers import RestaurantSerializer

@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})

class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
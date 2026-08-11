from restaurants.models import Restaurant
from restaurants.services.filters import filter_restaurants


def search_restaurants(query_params):
    queryset = Restaurant.objects.all()
    return filter_restaurants(queryset, query_params)

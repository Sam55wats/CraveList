from django.db.models import Case, IntegerField, Value, When

from restaurants.models import Restaurant
from restaurants.services.filters import filter_restaurants


def recommend_restaurants(user, query_params):
    queryset = Restaurant.objects.filter(
        user_entries__user=user,
        user_entries__bookmarked=True,
        user_entries__visited=False,
    ).distinct()
    queryset = filter_restaurants(queryset, query_params)

    return queryset.annotate(
        has_price=Case(
            When(price_level__isnull=False, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by("-has_price", "price_level", "name")

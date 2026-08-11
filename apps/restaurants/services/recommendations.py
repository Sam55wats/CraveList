from django.db.models import Q

from restaurants.models import Restaurant


def recommend_restaurants(user, query_params):
    queryset = Restaurant.objects.filter(
        user_entries__user=user,
        user_entries__bookmarked=True,
        user_entries__visited=False,
    ).distinct()

    search = query_params.get("search") or query_params.get("q")
    location = query_params.get("location")
    cuisine = query_params.get("cuisine")
    city = query_params.get("city")
    state = query_params.get("state")
    country = query_params.get("country")
    price_level = query_params.get("price_level")

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(cuisine__icontains=search)
            | Q(address__icontains=search)
        )

    if location:
        queryset = queryset.filter(
            Q(address__icontains=location)
            | Q(city__icontains=location)
            | Q(state__icontains=location)
            | Q(country__icontains=location)
        )

    if cuisine:
        queryset = queryset.filter(cuisine__icontains=cuisine)

    if city:
        queryset = queryset.filter(city__iexact=city)

    if state:
        queryset = queryset.filter(state__iexact=state)

    if country:
        queryset = queryset.filter(country__iexact=country)

    if price_level:
        queryset = queryset.filter(price_level=price_level)

    return queryset

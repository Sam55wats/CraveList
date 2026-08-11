from decimal import Decimal, InvalidOperation

from django.db.models import Q


def filter_restaurants(queryset, query_params, prefix=""):
    search = query_params.get("search") or query_params.get("q")
    location = query_params.get("location")
    cuisine = query_params.get("cuisine")
    address = query_params.get("address")
    city = query_params.get("city")
    state = query_params.get("state")
    country = query_params.get("country")
    price_level = query_params.get("price_level")
    external_source = query_params.get("external_source")

    name_field = f"{prefix}name"
    cuisine_field = f"{prefix}cuisine"
    address_field = f"{prefix}address"
    city_field = f"{prefix}city"
    state_field = f"{prefix}state"
    country_field = f"{prefix}country"
    price_level_field = f"{prefix}price_level"
    external_source_field = f"{prefix}external_source"

    if search:
        queryset = queryset.filter(
            Q(**{f"{name_field}__icontains": search})
            | Q(**{f"{cuisine_field}__icontains": search})
            | Q(**{f"{address_field}__icontains": search})
        )

    if location:
        queryset = queryset.filter(
            Q(**{f"{address_field}__icontains": location})
            | Q(**{f"{city_field}__icontains": location})
            | Q(**{f"{state_field}__icontains": location})
            | Q(**{f"{country_field}__icontains": location})
        )

    if cuisine:
        queryset = queryset.filter(**{f"{cuisine_field}__icontains": cuisine})

    if address:
        queryset = queryset.filter(**{f"{address_field}__icontains": address})

    if city:
        queryset = queryset.filter(**{f"{city_field}__iexact": city})

    if state:
        queryset = queryset.filter(**{f"{state_field}__iexact": state})

    if country:
        queryset = queryset.filter(**{f"{country_field}__iexact": country})

    if price_level:
        queryset = queryset.filter(**{price_level_field: price_level})

    if external_source:
        queryset = queryset.filter(**{f"{external_source_field}__iexact": external_source})

    return queryset


def filter_user_restaurants(queryset, query_params):
    bookmarked = query_params.get("bookmarked")
    visited = query_params.get("visited")
    min_rating = query_params.get("min_rating")

    if bookmarked is not None:
        queryset = queryset.filter(bookmarked=bookmarked.lower() == "true")

    if visited is not None:
        queryset = queryset.filter(visited=visited.lower() == "true")

    if min_rating:
        try:
            queryset = queryset.filter(rating__gte=Decimal(min_rating))
        except InvalidOperation:
            queryset = queryset.none()

    return filter_restaurants(queryset, query_params, prefix="restaurant__")

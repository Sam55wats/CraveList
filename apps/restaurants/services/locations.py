from django.db.models import Q

from restaurants.models import Restaurant


def suggest_locations(query, limit=10):
    query = (query or "").strip()

    if not query:
        return []

    location_rows = (
        Restaurant.objects.exclude(city="")
        .filter(
            Q(city__icontains=query)
            | Q(state__icontains=query)
            | Q(country__icontains=query)
        )
        .order_by("city", "state", "country")
        .values("city", "state", "country")
        .distinct()
    )

    suggestions = []
    seen_locations = set()

    for location in location_rows:
        city = location["city"]
        state = location["state"]
        country = location["country"]
        location_key = (city.lower(), state.lower(), country.lower())

        if location_key in seen_locations:
            continue

        seen_locations.add(location_key)
        label = ", ".join(part for part in (city, state, country) if part)
        suggestions.append(
            {
                "label": label,
                "city": city,
                "state": state,
                "country": country,
            }
        )

        if len(suggestions) == limit:
            break

    return suggestions

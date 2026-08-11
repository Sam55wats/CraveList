import json
from pathlib import Path

from .base import ProviderRestaurant, RestaurantProvider


class SeedRestaurantProvider(RestaurantProvider):
    source = "seed"

    def __init__(self, fixture_name="development_restaurants.json"):
        self.fixture_path = (
            Path(__file__).resolve().parents[2] / "fixtures" / fixture_name
        )

    def search(self, query_params):
        query = (query_params.get("q") or query_params.get("search") or "").lower()
        location = (query_params.get("location") or "").lower()
        cuisine = (query_params.get("cuisine") or "").lower()
        city = (query_params.get("city") or "").lower()
        price_level = query_params.get("price_level")
        try:
            limit = min(int(query_params.get("limit", 10)), 50)
        except ValueError:
            limit = 10

        matches = []

        for restaurant in self._load_restaurants():
            if query and not self._matches_query(restaurant, query):
                continue

            if location and not self._matches_location(restaurant, location):
                continue

            if cuisine and cuisine not in restaurant.cuisine.lower():
                continue

            if city and city != restaurant.city.lower():
                continue

            if price_level and str(restaurant.price_level) != price_level:
                continue

            matches.append(restaurant)

            if len(matches) == limit:
                break

        return matches

    def get(self, external_place_id):
        for restaurant in self._load_restaurants():
            if restaurant.external_place_id == external_place_id:
                return restaurant

        return None

    def _load_restaurants(self):
        restaurants = json.loads(self.fixture_path.read_text(encoding="utf-8"))

        return [
            ProviderRestaurant(
                name=restaurant["name"],
                address=restaurant.get("address", ""),
                cuisine=restaurant.get("cuisine", ""),
                price_level=restaurant.get("price_level"),
                city=restaurant.get("city", ""),
                state=restaurant.get("state", ""),
                country=restaurant.get("country", ""),
                latitude=restaurant.get("latitude"),
                longitude=restaurant.get("longitude"),
                external_place_id=restaurant["external_place_id"],
                external_source=restaurant["external_source"],
            )
            for restaurant in restaurants
        ]

    def _matches_query(self, restaurant, query):
        return any(
            query in value.lower()
            for value in (
                restaurant.name,
                restaurant.cuisine,
                restaurant.address,
            )
        )

    def _matches_location(self, restaurant, location):
        return any(
            location in value.lower()
            for value in (
                restaurant.address,
                restaurant.city,
                restaurant.state,
                restaurant.country,
            )
        )

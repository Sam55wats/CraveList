from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from .models import Follow, Restaurant, UserRestaurant
from .serializers import RestaurantSerializer


User = get_user_model()


class RestaurantAPITests(APITestCase):
    def test_restaurant_api_is_read_only(self):
        restaurant = Restaurant.objects.create(name="Taco Bamba")

        response = self.client.post(
            "/api/restaurants/",
            {
                "name": "User-Created Restaurant",
            },
            format="json",
        )
        update_response = self.client.patch(
            f"/api/restaurants/{restaurant.id}/",
            {"name": "Changed Name"},
            format="json",
        )
        delete_response = self.client.delete(f"/api/restaurants/{restaurant.id}/")

        self.assertEqual(response.status_code, 405)
        self.assertEqual(update_response.status_code, 405)
        self.assertEqual(delete_response.status_code, 405)
        self.assertEqual(Restaurant.objects.count(), 1)
        self.assertEqual(Restaurant.objects.first().name, "Taco Bamba")

    def test_price_level_must_be_between_one_and_four(self):
        serializer = RestaurantSerializer(
            data={
                "name": "Too Fancy",
                "price_level": 5,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("price_level", serializer.errors)

    def test_can_search_restaurants_by_name(self):
        Restaurant.objects.create(name="Taco Bamba", cuisine="Mexican")
        Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")

        response = self.client.get("/api/restaurants/?search=taco")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Taco Bamba")

    def test_can_search_restaurants_across_restaurant_fields(self):
        Restaurant.objects.create(
            name="Northwest Chinese",
            address="7313 Baltimore Ave",
            cuisine="Chinese",
            city="College Park",
            state="MD",
            country="USA",
        )
        Restaurant.objects.create(
            name="Taco Bamba",
            address="7777 Baltimore Ave",
            cuisine="Mexican",
            city="College Park",
            state="MD",
            country="USA",
        )

        cuisine_response = self.client.get("/api/restaurants/?q=chinese")
        address_response = self.client.get("/api/restaurants/?q=7313")

        self.assertEqual(cuisine_response.status_code, 200)
        self.assertEqual(cuisine_response.data["count"], 1)
        self.assertEqual(
            cuisine_response.data["results"][0]["name"], "Northwest Chinese"
        )

        self.assertEqual(address_response.status_code, 200)
        self.assertEqual(address_response.data["count"], 1)
        self.assertEqual(
            address_response.data["results"][0]["name"], "Northwest Chinese"
        )

    def test_location_parameter_searches_location_fields(self):
        Restaurant.objects.create(
            name="Northwest Chinese",
            cuisine="Chinese",
            city="College Park",
            state="MD",
            country="USA",
        )
        Restaurant.objects.create(
            name="Toronto Tacos",
            cuisine="Mexican",
            city="Toronto",
            state="ON",
            country="Canada",
        )

        response = self.client.get("/api/restaurants/search/?location=college")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Northwest Chinese")

    def test_can_filter_restaurants_by_cuisine_city_and_price(self):
        Restaurant.objects.create(
            name="Taco Bamba",
            cuisine="Mexican",
            city="College Park",
            price_level=2,
        )
        Restaurant.objects.create(
            name="Fancy Tacos",
            cuisine="Mexican",
            city="Washington",
            price_level=4,
        )

        response = self.client.get(
            "/api/restaurants/?cuisine=mexican&city=college%20park&price_level=2"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Taco Bamba")

    def test_search_endpoint_can_search_restaurants(self):
        Restaurant.objects.create(
            name="Northwest Chinese",
            cuisine="Chinese",
            city="College Park",
            price_level=2,
        )
        Restaurant.objects.create(
            name="Sushi Spot",
            cuisine="Japanese",
            city="College Park",
            price_level=3,
        )

        response = self.client.get("/api/restaurants/search/?q=chinese")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Northwest Chinese")

    def test_search_endpoint_supports_combined_filters(self):
        Restaurant.objects.create(
            name="Taco Bamba",
            cuisine="Mexican",
            city="College Park",
            price_level=2,
        )
        Restaurant.objects.create(
            name="Fancy Tacos",
            cuisine="Mexican",
            city="Washington",
            price_level=4,
        )

        response = self.client.get(
            "/api/restaurants/search/?q=taco&location=college&price_level=2"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Taco Bamba")

    def test_location_suggestions_returns_matching_locations(self):
        Restaurant.objects.create(
            name="Taco Bamba",
            cuisine="Mexican",
            city="College Park",
            state="MD",
            country="USA",
        )
        Restaurant.objects.create(
            name="Northwest Chinese",
            cuisine="Chinese",
            city="College Park",
            state="MD",
            country="USA",
        )
        Restaurant.objects.create(
            name="Columbia Cafe",
            cuisine="Cafe",
            city="Columbia",
            state="MD",
            country="USA",
        )
        Restaurant.objects.create(
            name="Toronto Tacos",
            cuisine="Mexican",
            city="Toronto",
            state="ON",
            country="Canada",
        )

        response = self.client.get("/api/restaurants/location-suggestions/?q=col")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            [
                {
                    "label": "College Park, MD, USA",
                    "city": "College Park",
                    "state": "MD",
                    "country": "USA",
                },
                {
                    "label": "Columbia, MD, USA",
                    "city": "Columbia",
                    "state": "MD",
                    "country": "USA",
                },
            ],
        )

    def test_location_suggestions_requires_a_query(self):
        Restaurant.objects.create(
            name="Taco Bamba",
            city="College Park",
            state="MD",
            country="USA",
        )

        response = self.client.get("/api/restaurants/location-suggestions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_can_filter_restaurants_by_state_country_and_external_source(self):
        Restaurant.objects.create(
            name="Taco Bamba",
            city="College Park",
            state="MD",
            country="USA",
            external_source="google",
            external_place_id="google-123",
        )
        Restaurant.objects.create(
            name="Toronto Tacos",
            city="Toronto",
            state="ON",
            country="Canada",
            external_source="foursquare",
            external_place_id="fsq-123",
        )

        response = self.client.get(
            "/api/restaurants/?state=md&country=usa&external_source=google"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Taco Bamba")

    def test_cuisine_filter_allows_partial_matches(self):
        Restaurant.objects.create(name="Taco Bamba", cuisine="Mexican")
        Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")

        response = self.client.get("/api/restaurants/?cuisine=mex")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Taco Bamba")

    def test_restaurant_list_is_paginated(self):
        Restaurant.objects.bulk_create(
            [Restaurant(name=f"Restaurant {number:02d}") for number in range(25)]
        )

        response = self.client.get("/api/restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_restaurant_list_accepts_page_size_with_a_safe_maximum(self):
        Restaurant.objects.bulk_create(
            [Restaurant(name=f"Restaurant {number:03d}") for number in range(105)]
        )

        response = self.client.get("/api/restaurants/?page_size=500")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 105)
        self.assertEqual(len(response.data["results"]), 100)

    def test_restaurants_can_be_ordered_by_allowed_fields(self):
        Restaurant.objects.create(name="Alpha Cafe", price_level=1)
        Restaurant.objects.create(name="Charlie Kitchen", price_level=3)
        Restaurant.objects.create(name="Bravo Bistro", price_level=2)

        response = self.client.get("/api/restaurants/?ordering=-price_level")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [restaurant["name"] for restaurant in response.data["results"]],
            ["Charlie Kitchen", "Bravo Bistro", "Alpha Cafe"],
        )

    def test_search_endpoint_applies_pagination_and_ordering(self):
        Restaurant.objects.bulk_create(
            [
                Restaurant(name=f"Taco Place {number:02d}", cuisine="Mexican")
                for number in range(25)
            ]
        )

        response = self.client.get(
            "/api/restaurants/search/?q=taco&page_size=5&ordering=-name"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(response.data["results"][0]["name"], "Taco Place 24")


class SeedRestaurantsCommandTests(APITestCase):
    def test_seed_restaurants_loads_development_restaurants(self):
        call_command("seed_restaurants")

        self.assertEqual(Restaurant.objects.count(), 40)
        self.assertTrue(
            Restaurant.objects.filter(
                external_source="seed",
                external_place_id="seed-college-park-taco-bamba",
            ).exists()
        )

    def test_seed_restaurants_is_idempotent(self):
        call_command("seed_restaurants")
        call_command("seed_restaurants")

        self.assertEqual(Restaurant.objects.count(), 40)


class UserRestaurantAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="samuel", password="password")
        self.other_user = User.objects.create_user(username="other", password="password")
        self.restaurant = Restaurant.objects.create(
            name="Taco Bamba",
            cuisine="Mexican",
            city="College Park",
            price_level=2,
        )
        self.client.force_authenticate(user=self.user)

    def test_can_bookmark_restaurant_for_current_user(self):
        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "bookmarked": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserRestaurant.objects.count(), 1)
        entry = UserRestaurant.objects.first()
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.restaurant, self.restaurant)
        self.assertTrue(entry.bookmarked)

    def test_can_rate_visited_restaurant_with_decimal_score(self):
        entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            visited=True,
        )

        response = self.client.patch(
            f"/api/my-restaurants/{entry.id}/",
            {
                "rating": "9.2",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(str(entry.rating), "9.2")

    def test_rating_must_be_between_one_and_ten(self):
        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "visited": True,
                "rating": "10.1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.data)

    def test_rating_requires_visited_true(self):
        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "visited": False,
                "rating": "9.2",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.data)

    def test_user_only_sees_their_own_restaurant_entries(self):
        UserRestaurant.objects.create(user=self.user, restaurant=self.restaurant)
        other_restaurant = Restaurant.objects.create(name="Other Place")
        UserRestaurant.objects.create(user=self.other_user, restaurant=other_restaurant)

        response = self.client.get("/api/my-restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["restaurant"]["name"], "Taco Bamba")

    def test_can_filter_user_restaurants_by_visited_and_cuisine(self):
        UserRestaurant.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            visited=True,
            rating="9.2",
        )
        sushi = Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")
        UserRestaurant.objects.create(user=self.user, restaurant=sushi, visited=False)

        response = self.client.get("/api/my-restaurants/?visited=true&cuisine=mexican")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["restaurant"]["name"], "Taco Bamba")

    def test_authentication_is_required_for_user_restaurants(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/my-restaurants/")

        self.assertEqual(response.status_code, 403)


class FollowAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="samuel", password="password")
        self.friend = User.objects.create_user(username="friend", password="password")
        self.client.force_authenticate(user=self.user)

    def test_can_follow_another_user(self):
        response = self.client.post(
            "/api/follows/",
            {
                "following_id": self.friend.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Follow.objects.count(), 1)
        follow = Follow.objects.first()
        self.assertEqual(follow.follower, self.user)
        self.assertEqual(follow.following, self.friend)

    def test_user_cannot_follow_themself(self):
        response = self.client.post(
            "/api/follows/",
            {
                "following_id": self.user.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("following_id", response.data)

    def test_user_only_sees_people_they_follow(self):
        Follow.objects.create(follower=self.user, following=self.friend)
        other_user = User.objects.create_user(username="other", password="password")
        Follow.objects.create(follower=self.friend, following=other_user)

        response = self.client.get("/api/follows/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["following"], "friend")

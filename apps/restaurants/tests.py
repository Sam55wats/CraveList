from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Follow, Restaurant, UserRestaurant


User = get_user_model()


class RestaurantAPITests(APITestCase):
    def test_can_create_restaurant_facts(self):
        response = self.client.post(
            "/api/restaurants/",
            {
                "name": "Taco Bamba",
                "address": "7777 Baltimore Ave",
                "cuisine": "Mexican",
                "price_level": 2,
                "city": "College Park",
                "state": "MD",
                "external_place_id": "places_123",
                "external_source": "google",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Restaurant.objects.count(), 1)
        self.assertEqual(Restaurant.objects.first().name, "Taco Bamba")

    def test_price_level_must_be_between_one_and_four(self):
        response = self.client.post(
            "/api/restaurants/",
            {
                "name": "Too Fancy",
                "price_level": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("price_level", response.data)

    def test_can_search_restaurants_by_name(self):
        Restaurant.objects.create(name="Taco Bamba", cuisine="Mexican")
        Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")

        response = self.client.get("/api/restaurants/?search=taco")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Taco Bamba")

    def test_can_search_restaurants_across_core_fields(self):
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
        city_response = self.client.get("/api/restaurants/?q=college")
        address_response = self.client.get("/api/restaurants/?q=7313")

        self.assertEqual(cuisine_response.status_code, 200)
        self.assertEqual(len(cuisine_response.data), 1)
        self.assertEqual(cuisine_response.data[0]["name"], "Northwest Chinese")

        self.assertEqual(city_response.status_code, 200)
        self.assertEqual(len(city_response.data), 2)

        self.assertEqual(address_response.status_code, 200)
        self.assertEqual(len(address_response.data), 1)
        self.assertEqual(address_response.data[0]["name"], "Northwest Chinese")

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
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Taco Bamba")

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
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Taco Bamba")

    def test_cuisine_filter_allows_partial_matches(self):
        Restaurant.objects.create(name="Taco Bamba", cuisine="Mexican")
        Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")

        response = self.client.get("/api/restaurants/?cuisine=mex")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Taco Bamba")


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

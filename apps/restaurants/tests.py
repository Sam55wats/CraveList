import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import Follow, Restaurant, UserRestaurant, UserRestaurantPhoto
from .serializers import RestaurantSerializer


User = get_user_model()
TEST_MEDIA_ROOT = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


def get_test_image(name="test.gif"):
    return SimpleUploadedFile(
        name,
        (
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


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

    def test_restaurant_results_include_current_users_entry_when_authenticated(self):
        user = User.objects.create_user(username="samuel", password="password")
        taco_bamba = Restaurant.objects.create(name="Taco Bamba", cuisine="Mexican")
        Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")
        entry = UserRestaurant.objects.create(
            user=user,
            restaurant=taco_bamba,
            bookmarked=True,
            visited=True,
            rating="9.2",
            notes="Loved the tacos.",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/restaurants/?ordering=-name")

        self.assertEqual(response.status_code, 200)
        taco_result = response.data["results"][0]
        sushi_result = response.data["results"][1]
        self.assertEqual(taco_result["name"], "Taco Bamba")
        self.assertEqual(taco_result["my_entry"]["id"], entry.id)
        self.assertTrue(taco_result["my_entry"]["bookmarked"])
        self.assertTrue(taco_result["my_entry"]["visited"])
        self.assertEqual(taco_result["my_entry"]["rating"], "9.2")
        self.assertEqual(taco_result["my_entry"]["notes"], "Loved the tacos.")
        self.assertIsNone(sushi_result["my_entry"])

    def test_restaurant_results_have_no_my_entry_for_anonymous_users(self):
        Restaurant.objects.create(name="Taco Bamba", cuisine="Mexican")

        response = self.client.get("/api/restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["results"][0]["my_entry"])

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

    def test_saving_same_restaurant_twice_returns_existing_entry(self):
        first_response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
            },
            format="json",
        )
        second_response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
            },
            format="json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(UserRestaurant.objects.count(), 1)
        self.assertEqual(first_response.data["id"], second_response.data["id"])
        self.assertTrue(second_response.data["bookmarked"])

    def test_saving_existing_unbookmarked_restaurant_rebookmarks_it(self):
        entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            bookmarked=False,
        )

        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertTrue(entry.bookmarked)

    def test_saving_existing_restaurant_can_update_visit_and_rating(self):
        entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            bookmarked=True,
        )

        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "visited": True,
                "rating": "8.7",
                "notes": "Great tacos.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserRestaurant.objects.count(), 1)
        entry.refresh_from_db()
        self.assertTrue(entry.visited)
        self.assertEqual(str(entry.rating), "8.7")
        self.assertEqual(entry.notes, "Great tacos.")
        self.assertFalse(entry.bookmarked)

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

    def test_visited_restaurant_requires_rating(self):
        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "visited": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.data)

    def test_notes_require_visited_restaurant(self):
        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "notes": "Want to try the tacos.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("notes", response.data)

    def test_notes_are_allowed_after_visiting_and_rating(self):
        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "visited": True,
                "rating": "9.2",
                "notes": "Loved the tacos.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        entry = UserRestaurant.objects.get()
        self.assertEqual(entry.notes, "Loved the tacos.")

    def test_visited_restaurant_is_automatically_unbookmarked(self):
        response = self.client.post(
            "/api/my-restaurants/",
            {
                "restaurant_id": self.restaurant.id,
                "bookmarked": True,
                "visited": True,
                "rating": "9.2",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        entry = UserRestaurant.objects.get()
        self.assertTrue(entry.visited)
        self.assertEqual(str(entry.rating), "9.2")
        self.assertFalse(entry.bookmarked)

    def test_can_unbookmark_without_removing_visit_history(self):
        entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            bookmarked=True,
            visited=True,
            rating="9.2",
        )

        response = self.client.patch(
            f"/api/my-restaurants/{entry.id}/",
            {
                "bookmarked": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertFalse(entry.bookmarked)
        self.assertTrue(entry.visited)
        self.assertEqual(str(entry.rating), "9.2")

    def test_can_delete_user_restaurant_without_deleting_restaurant(self):
        entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            visited=True,
            rating="9.2",
        )

        response = self.client.delete(f"/api/my-restaurants/{entry.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(UserRestaurant.objects.count(), 0)
        self.assertTrue(Restaurant.objects.filter(id=self.restaurant.id).exists())

    def test_user_only_sees_their_own_restaurant_entries(self):
        UserRestaurant.objects.create(user=self.user, restaurant=self.restaurant)
        other_restaurant = Restaurant.objects.create(name="Other Place")
        UserRestaurant.objects.create(user=self.other_user, restaurant=other_restaurant)

        response = self.client.get("/api/my-restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["restaurant"]["name"], "Taco Bamba")

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
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["restaurant"]["name"], "Taco Bamba")

    def test_user_restaurants_are_paginated(self):
        created_restaurants = [
            self.restaurant,
            *Restaurant.objects.bulk_create(
                [Restaurant(name=f"Restaurant {number:02d}") for number in range(24)]
            ),
        ]
        UserRestaurant.objects.bulk_create(
            [
                UserRestaurant(user=self.user, restaurant=restaurant)
                for restaurant in created_restaurants
            ]
        )

        response = self.client.get("/api/my-restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_user_restaurants_can_be_ordered_by_rating_descending(self):
        sushi = Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")
        pizza = Restaurant.objects.create(name="Pizza Place", cuisine="Italian")
        UserRestaurant.objects.create(
            user=self.user,
            restaurant=sushi,
            visited=True,
            rating="7.8",
        )
        UserRestaurant.objects.create(
            user=self.user,
            restaurant=pizza,
            visited=True,
            rating="9.4",
        )

        response = self.client.get("/api/my-restaurants/?ordering=-rating")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [entry["restaurant"]["name"] for entry in response.data["results"]],
            ["Pizza Place", "Sushi Spot"],
        )

    def test_authentication_is_required_for_user_restaurants(self):
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/my-restaurants/")

        self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class UserRestaurantPhotoAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="samuel", password="password")
        self.other_user = User.objects.create_user(username="other", password="password")
        self.restaurant = Restaurant.objects.create(name="Taco Bamba")
        self.entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=self.restaurant,
            visited=True,
            rating="9.2",
        )
        self.client.force_authenticate(user=self.user)

    def test_can_upload_photo_for_visited_rated_restaurant_entry(self):
        response = self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": self.entry.id,
                "image": get_test_image(),
                "description": "Tacos from lunch.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserRestaurantPhoto.objects.count(), 1)
        photo = UserRestaurantPhoto.objects.get()
        self.assertEqual(photo.user_restaurant, self.entry)
        self.assertEqual(photo.description, "Tacos from lunch.")
        self.assertEqual(response.data["user"], "samuel")
        self.assertEqual(response.data["restaurant"]["name"], "Taco Bamba")

    def test_photo_description_is_required(self):
        response = self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": self.entry.id,
                "image": get_test_image(),
                "description": "   ",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("description", response.data)

    def test_photo_requires_visited_rated_restaurant_entry(self):
        unvisited_entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=Restaurant.objects.create(name="Sushi Spot"),
        )

        response = self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": unvisited_entry.id,
                "image": get_test_image(),
                "description": "Sushi photo.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("user_restaurant_id", response.data)

    def test_user_cannot_upload_photo_to_another_users_entry(self):
        other_entry = UserRestaurant.objects.create(
            user=self.other_user,
            restaurant=Restaurant.objects.create(name="Other Place"),
            visited=True,
            rating="8.1",
        )

        response = self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": other_entry.id,
                "image": get_test_image(),
                "description": "Not my visit.",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("user_restaurant_id", response.data)

    def test_photos_are_publicly_readable(self):
        upload_response = self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": self.entry.id,
                "image": get_test_image(),
                "description": "Public taco photo.",
            },
            format="multipart",
        )
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/my-restaurant-photos/")

        self.assertEqual(upload_response.status_code, 201)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["description"], "Public taco photo.")

    def test_can_filter_photos_by_restaurant(self):
        self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": self.entry.id,
                "image": get_test_image(),
                "description": "Taco photo.",
            },
            format="multipart",
        )
        other_restaurant = Restaurant.objects.create(name="Pizza Place")
        other_entry = UserRestaurant.objects.create(
            user=self.user,
            restaurant=other_restaurant,
            visited=True,
            rating="7.5",
        )
        self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": other_entry.id,
                "image": get_test_image("pizza.gif"),
                "description": "Pizza photo.",
            },
            format="multipart",
        )

        response = self.client.get(
            f"/api/my-restaurant-photos/?restaurant_id={self.restaurant.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["description"], "Taco photo.")

    def test_user_can_delete_their_own_photo(self):
        upload_response = self.client.post(
            "/api/my-restaurant-photos/",
            {
                "user_restaurant_id": self.entry.id,
                "image": get_test_image(),
                "description": "Delete this photo.",
            },
            format="multipart",
        )

        response = self.client.delete(
            f"/api/my-restaurant-photos/{upload_response.data['id']}/"
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(UserRestaurantPhoto.objects.count(), 0)

    def test_user_cannot_delete_another_users_photo(self):
        photo = UserRestaurantPhoto.objects.create(
            user_restaurant=self.entry,
            image=get_test_image(),
            description="Someone else's viewable photo.",
        )
        self.client.force_authenticate(user=self.other_user)

        response = self.client.delete(f"/api/my-restaurant-photos/{photo.id}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(UserRestaurantPhoto.objects.filter(id=photo.id).exists())


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

from rest_framework.test import APITestCase

from .models import Restaurant


class RestaurantSerializerValidationTests(APITestCase):
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

    def test_rating_must_be_between_one_and_five(self):
        response = self.client.post(
            "/api/restaurants/",
            {
                "name": "Impossible Rating",
                "visited": True,
                "rating": 6,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.data)

    def test_rating_requires_visited_true(self):
        response = self.client.post(
            "/api/restaurants/",
            {
                "name": "Not Yet Visited",
                "visited": False,
                "rating": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("rating", response.data)

    def test_valid_visited_rating_can_be_saved(self):
        response = self.client.post(
            "/api/restaurants/",
            {
                "name": "Good Dinner",
                "price_level": 3,
                "visited": True,
                "rating": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Restaurant.objects.filter(name="Good Dinner").exists())


class RestaurantAPICRUDTests(APITestCase):
    def test_can_create_restaurant(self):
        response = self.client.post(
            "/api/restaurants/",
            {
                "name": "Taco Bamba",
                "cuisine": "Mexican",
                "price_level": 2,
                "city": "College Park",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Restaurant.objects.count(), 1)
        self.assertEqual(Restaurant.objects.first().name, "Taco Bamba")

    def test_can_list_restaurants(self):
        Restaurant.objects.create(name="Taco Bamba")
        Restaurant.objects.create(name="Sushi Spot")

        response = self.client.get("/api/restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_can_retrieve_restaurant(self):
        restaurant = Restaurant.objects.create(name="Taco Bamba")

        response = self.client.get(f"/api/restaurants/{restaurant.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Taco Bamba")

    def test_can_update_restaurant(self):
        restaurant = Restaurant.objects.create(name="Taco Bamba", visited=False)

        response = self.client.patch(
            f"/api/restaurants/{restaurant.id}/",
            {
                "visited": True,
                "rating": 5,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        restaurant.refresh_from_db()
        self.assertTrue(restaurant.visited)
        self.assertEqual(restaurant.rating, 5)

    def test_can_delete_restaurant(self):
        restaurant = Restaurant.objects.create(name="Taco Bamba")

        response = self.client.delete(f"/api/restaurants/{restaurant.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(Restaurant.objects.count(), 0)

    def test_restaurants_are_ordered_newest_first(self):
        first = Restaurant.objects.create(name="First")
        second = Restaurant.objects.create(name="Second")

        response = self.client.get("/api/restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["id"], second.id)
        self.assertEqual(response.data[1]["id"], first.id)


class RestaurantAPIFilterTests(APITestCase):
    def test_can_filter_by_visited(self):
        Restaurant.objects.create(name="Visited", visited=True)
        Restaurant.objects.create(name="Not Visited", visited=False)

        response = self.client.get("/api/restaurants/?visited=false")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Not Visited")

    def test_can_filter_by_cuisine_case_insensitively(self):
        Restaurant.objects.create(name="Taco Bamba", cuisine="Mexican")
        Restaurant.objects.create(name="Sushi Spot", cuisine="Japanese")

        response = self.client.get("/api/restaurants/?cuisine=mexican")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Taco Bamba")

    def test_can_filter_by_city_case_insensitively(self):
        Restaurant.objects.create(name="Taco Bamba", city="College Park")
        Restaurant.objects.create(name="DC Noodles", city="Washington")

        response = self.client.get("/api/restaurants/?city=college%20park")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Taco Bamba")

    def test_can_filter_by_price_level(self):
        Restaurant.objects.create(name="Cheap Eats", price_level=1)
        Restaurant.objects.create(name="Date Night", price_level=3)

        response = self.client.get("/api/restaurants/?price_level=3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Date Night")

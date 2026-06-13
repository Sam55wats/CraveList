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

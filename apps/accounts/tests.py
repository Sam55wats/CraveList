from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from restaurants.models import Follow, Restaurant, UserRestaurant


User = get_user_model()


class AuthEndpointTests(APITestCase):
    def test_can_get_csrf_token_for_frontend_session_requests(self):
        response = self.client.get("/api/auth/csrf/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.data)
        self.assertIn("csrftoken", response.cookies)
        self.assertTrue(response.data["csrfToken"])
        self.assertTrue(response.cookies["csrftoken"].value)

    def test_can_register_and_is_logged_in(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "samuel",
                "email": "samuel@example.com",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], "samuel")
        self.assertNotIn("password", response.data)
        self.assertTrue(User.objects.filter(username="samuel").exists())

        me_response = self.client.get("/api/auth/me/")

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["username"], "samuel")

    def test_cannot_register_with_duplicate_username(self):
        User.objects.create_user(username="samuel", password="StrongPass123!")

        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "samuel",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_can_login_and_fetch_current_user(self):
        User.objects.create_user(username="samuel", password="StrongPass123!")

        login_response = self.client.post(
            "/api/auth/login/",
            {
                "username": "samuel",
                "password": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data["username"], "samuel")

        me_response = self.client.get("/api/auth/me/")

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data["username"], "samuel")

    def test_login_rejects_invalid_credentials(self):
        User.objects.create_user(username="samuel", password="StrongPass123!")

        response = self.client.post(
            "/api/auth/login/",
            {
                "username": "samuel",
                "password": "wrong-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Invalid username or password.")

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 403)

    def test_can_logout(self):
        user = User.objects.create_user(username="samuel", password="StrongPass123!")
        self.client.force_authenticate(user=user)

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], "Logged out.")

    def test_session_authenticated_post_requires_csrf_when_csrf_checks_are_enabled(self):
        client = APIClient(enforce_csrf_checks=True)
        User.objects.create_user(username="samuel", password="StrongPass123!")
        client.login(username="samuel", password="StrongPass123!")

        response = client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 403)

    def test_session_authenticated_post_accepts_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        User.objects.create_user(username="samuel", password="StrongPass123!")
        client.login(username="samuel", password="StrongPass123!")
        csrf_response = client.get("/api/auth/csrf/")
        csrf_token = csrf_response.data["csrfToken"]

        response = client.post(
            "/api/auth/logout/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["detail"], "Logged out.")


class PublicUserAPITests(APITestCase):
    def test_can_list_public_users_without_private_email(self):
        User.objects.create_user(
            username="samuel",
            email="samuel@example.com",
            password="password",
        )
        User.objects.create_user(username="friend", password="password")

        response = self.client.get("/api/users/?ordering=username")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["username"], "friend")
        self.assertNotIn("email", response.data["results"][0])
        self.assertIn("followers_count", response.data["results"][0])
        self.assertIn("following_count", response.data["results"][0])
        self.assertIn("visited_count", response.data["results"][0])
        self.assertIn("bookmarked_count", response.data["results"][0])
        self.assertIn("average_rating", response.data["results"][0])

    def test_public_user_detail_includes_follow_status_for_logged_in_user(self):
        user = User.objects.create_user(username="samuel", password="password")
        friend = User.objects.create_user(username="friend", password="password")
        follow = Follow.objects.create(follower=user, following=friend)
        self.client.force_authenticate(user=user)

        response = self.client.get(f"/api/users/{friend.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], "friend")
        self.assertTrue(response.data["is_following"])
        self.assertEqual(response.data["follow_id"], follow.id)
        self.assertEqual(response.data["followers_count"], 1)

    def test_public_user_detail_includes_restaurant_stats(self):
        friend = User.objects.create_user(username="friend", password="password")
        taco_bamba = Restaurant.objects.create(name="Taco Bamba")
        sushi_spot = Restaurant.objects.create(name="Sushi Spot")
        UserRestaurant.objects.create(
            user=friend,
            restaurant=taco_bamba,
            bookmarked=False,
            visited=True,
            rating="9.0",
        )
        UserRestaurant.objects.create(
            user=friend,
            restaurant=sushi_spot,
            bookmarked=True,
            visited=False,
        )

        response = self.client.get(f"/api/users/{friend.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["visited_count"], 1)
        self.assertEqual(response.data["bookmarked_count"], 1)
        self.assertEqual(response.data["average_rating"], "9.0")

    def test_public_user_restaurants_only_shows_visited_rated_entries(self):
        friend = User.objects.create_user(username="friend", password="password")
        taco_bamba = Restaurant.objects.create(name="Taco Bamba")
        sushi_spot = Restaurant.objects.create(name="Sushi Spot")
        UserRestaurant.objects.create(
            user=friend,
            restaurant=taco_bamba,
            visited=True,
            rating="9.2",
            notes="Loved it.",
        )
        UserRestaurant.objects.create(
            user=friend,
            restaurant=sushi_spot,
            bookmarked=True,
        )

        response = self.client.get(f"/api/users/{friend.id}/restaurants/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["restaurant"]["name"], "Taco Bamba")
        self.assertEqual(response.data["results"][0]["rating"], "9.2")

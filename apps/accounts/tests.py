from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


User = get_user_model()


class AuthEndpointTests(APITestCase):
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

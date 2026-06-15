from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    cuisine = models.CharField(max_length=255, blank=True)
    price_level = models.PositiveSmallIntegerField(null=True, blank=True)
    city = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    external_place_id = models.CharField(max_length=255, blank=True)
    external_source = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_source", "external_place_id"],
                condition=~Q(external_place_id=""),
                name="unique_restaurant_external_place",
            )
        ]

    def __str__(self):
        return self.name


class UserRestaurant(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="restaurant_entries",
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="user_entries",
    )
    bookmarked = models.BooleanField(default=True)
    visited = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    notes = models.TextField(blank=True)
    visited_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "restaurant"],
                name="unique_user_restaurant",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.restaurant}"


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following_relationships",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follower_relationships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_follow_relationship",
            ),
            models.CheckConstraint(
                condition=~Q(follower=F("following")),
                name="prevent_self_follow",
            ),
        ]

    def __str__(self):
        return f"{self.follower} follows {self.following}"

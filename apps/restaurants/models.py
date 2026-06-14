from django.db import models


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    cuisine = models.CharField(max_length=255, blank=True)
    price_level = models.PositiveSmallIntegerField(null=True, blank=True)
    city = models.CharField(max_length=255, blank=True)
    vibe = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    visited = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    visited_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

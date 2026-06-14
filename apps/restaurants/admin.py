from django.contrib import admin
from .models import Restaurant


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "cuisine",
        "city",
        "price_level",
        "visited",
        "rating",
        "updated_at",
    )
    list_filter = (
        "visited",
        "price_level",
        "cuisine",
        "city",
    )
    search_fields = (
        "name",
        "cuisine",
        "city",
        "vibe",
        "notes",
    )

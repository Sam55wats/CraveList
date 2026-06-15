from django.contrib import admin

from .models import Follow, Restaurant, UserRestaurant


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "cuisine",
        "city",
        "state",
        "price_level",
        "external_source",
        "updated_at",
    )
    list_filter = (
        "price_level",
        "cuisine",
        "city",
        "state",
        "external_source",
    )
    search_fields = (
        "name",
        "address",
        "cuisine",
        "city",
        "state",
        "external_place_id",
    )


@admin.register(UserRestaurant)
class UserRestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "restaurant",
        "bookmarked",
        "visited",
        "rating",
        "visited_at",
        "updated_at",
    )
    list_filter = (
        "bookmarked",
        "visited",
        "rating",
        "restaurant__cuisine",
        "restaurant__city",
    )
    search_fields = (
        "user__username",
        "restaurant__name",
        "restaurant__city",
        "notes",
    )
    autocomplete_fields = ("restaurant",)


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = (
        "follower",
        "following",
        "created_at",
    )
    search_fields = (
        "follower__username",
        "following__username",
    )

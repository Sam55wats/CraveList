from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Follow, Restaurant, UserRestaurant, UserRestaurantPhoto


User = get_user_model()


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = "__all__"

    def validate_price_level(self, value):
        if value is not None and not 1 <= value <= 4:
            raise serializers.ValidationError("Price level must be between 1 and 4.")
        return value


class UserRestaurantSerializer(serializers.ModelSerializer):
    restaurant = RestaurantSerializer(read_only=True)
    restaurant_id = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.all(),
        source="restaurant",
        write_only=True,
    )
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = UserRestaurant
        fields = (
            "id",
            "user",
            "restaurant",
            "restaurant_id",
            "bookmarked",
            "visited",
            "rating",
            "notes",
            "visited_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_rating(self, value):
        if value is not None and not Decimal("1.0") <= value <= Decimal("10.0"):
            raise serializers.ValidationError("Rating must be between 1.0 and 10.0.")
        return value

    def validate(self, data):
        visited = data.get("visited", getattr(self.instance, "visited", False))
        rating = data.get("rating", getattr(self.instance, "rating", None))
        notes = data.get("notes", getattr(self.instance, "notes", ""))

        if rating is not None and not visited:
            raise serializers.ValidationError(
                {"rating": "Rating can only be set after visiting the restaurant."}
            )

        if notes and not visited:
            raise serializers.ValidationError(
                {"notes": "Notes can only be added after visiting the restaurant."}
            )

        if visited and rating is None:
            raise serializers.ValidationError(
                {"rating": "Rating is required after visiting the restaurant."}
            )

        if visited:
            data["bookmarked"] = False

        return data


class UserRestaurantPhotoSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user_restaurant.user.username", read_only=True)
    restaurant = RestaurantSerializer(source="user_restaurant.restaurant", read_only=True)
    user_restaurant_id = serializers.PrimaryKeyRelatedField(
        queryset=UserRestaurant.objects.none(),
        source="user_restaurant",
        write_only=True,
    )

    class Meta:
        model = UserRestaurantPhoto
        fields = (
            "id",
            "user",
            "restaurant",
            "user_restaurant_id",
            "image",
            "description",
            "created_at",
        )
        read_only_fields = ("created_at",)

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")

        if request and request.user.is_authenticated:
            fields["user_restaurant_id"].queryset = UserRestaurant.objects.filter(
                user=request.user,
                visited=True,
                rating__isnull=False,
            )

        return fields

    def validate_description(self, value):
        if not value.strip():
            raise serializers.ValidationError("Description is required for photos.")
        return value


class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.StringRelatedField(read_only=True)
    following = serializers.StringRelatedField(read_only=True)
    following_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source="following",
        write_only=True,
    )

    class Meta:
        model = Follow
        fields = (
            "id",
            "follower",
            "following",
            "following_id",
            "created_at",
        )
        read_only_fields = ("created_at",)

    def validate_following_id(self, value):
        request = self.context.get("request")
        if request and request.user == value:
            raise serializers.ValidationError("You cannot follow yourself.")
        return value

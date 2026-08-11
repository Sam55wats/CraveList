from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Follow, Restaurant, UserRestaurant, UserRestaurantPhoto


User = get_user_model()


class RestaurantSerializer(serializers.ModelSerializer):
    my_entry = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = "__all__"

    def validate_price_level(self, value):
        if value is not None and not 1 <= value <= 4:
            raise serializers.ValidationError("Price level must be between 1 and 4.")
        return value

    def get_my_entry(self, restaurant):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        user_entries = getattr(restaurant, "current_user_entries", None)

        if user_entries is None:
            entry = UserRestaurant.objects.filter(
                user=request.user,
                restaurant=restaurant,
            ).first()
        else:
            entry = user_entries[0] if user_entries else None

        if entry is None:
            return None

        return {
            "id": entry.id,
            "bookmarked": entry.bookmarked,
            "visited": entry.visited,
            "rating": str(entry.rating) if entry.rating is not None else None,
            "notes": entry.notes,
            "visited_at": entry.visited_at,
            "updated_at": entry.updated_at,
        }


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

    def validate_image(self, value):
        max_photo_bytes = getattr(settings, "MAX_RESTAURANT_PHOTO_BYTES", 5 * 1024 * 1024)
        allowed_content_types = getattr(
            settings,
            "ALLOWED_RESTAURANT_PHOTO_CONTENT_TYPES",
            ["image/jpeg", "image/png", "image/webp", "image/gif"],
        )
        allowed_extensions = getattr(
            settings,
            "ALLOWED_RESTAURANT_PHOTO_EXTENSIONS",
            [".jpg", ".jpeg", ".png", ".webp", ".gif"],
        )

        if value.size > max_photo_bytes:
            raise serializers.ValidationError("Photo must be 5 MB or smaller.")

        if value.content_type not in allowed_content_types:
            raise serializers.ValidationError(
                "Photo must be a JPEG, PNG, WEBP, or GIF image."
            )

        if Path(value.name).suffix.lower() not in allowed_extensions:
            raise serializers.ValidationError(
                "Photo file extension must be JPG, PNG, WEBP, or GIF."
            )

        return value


class UserRestaurantPhotoSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserRestaurantPhoto
        fields = ("id", "image", "description", "created_at")


class UserRestaurantSerializer(serializers.ModelSerializer):
    restaurant = RestaurantSerializer(read_only=True)
    restaurant_id = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.all(),
        source="restaurant",
        write_only=True,
    )
    user = serializers.StringRelatedField(read_only=True)
    photos = UserRestaurantPhotoSummarySerializer(many=True, read_only=True)

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
            "photos",
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


class PublicUserRestaurantSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    restaurant = RestaurantSerializer(read_only=True)
    photos = UserRestaurantPhotoSummarySerializer(many=True, read_only=True)

    class Meta:
        model = UserRestaurant
        fields = (
            "id",
            "user",
            "restaurant",
            "visited",
            "rating",
            "notes",
            "visited_at",
            "photos",
            "created_at",
            "updated_at",
        )


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


class ExternalRestaurantImportSerializer(serializers.Serializer):
    external_source = serializers.CharField(default="seed")
    external_place_id = serializers.CharField()


class ExternalRestaurantImportAndSaveSerializer(ExternalRestaurantImportSerializer):
    bookmarked = serializers.BooleanField(default=True)
    visited = serializers.BooleanField(default=False)
    rating = serializers.DecimalField(
        max_digits=3,
        decimal_places=1,
        required=False,
        allow_null=True,
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    visited_at = serializers.DateField(required=False, allow_null=True)

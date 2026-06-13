from rest_framework import serializers
from .models import Restaurant


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = "__all__"

    def validate_price_level(self, value):
        if value is not None and not 1 <= value <= 4:
            raise serializers.ValidationError("Price level must be between 1 and 4.")
        return value

    def validate_rating(self, value):
        if value is not None and not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate(self, data):
        visited = data.get("visited", getattr(self.instance, "visited", False))
        rating = data.get("rating", getattr(self.instance, "rating", None))

        if rating is not None and not visited:
            raise serializers.ValidationError(
                {"rating": "Rating can only be set after visiting the restaurant."}
            )

        return data

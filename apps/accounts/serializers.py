from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class PublicUserSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    follow_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "followers_count",
            "following_count",
            "is_following",
            "follow_id",
        )

    def get_followers_count(self, user):
        if hasattr(user, "followers_count"):
            return user.followers_count

        return user.follower_relationships.count()

    def get_following_count(self, user):
        if hasattr(user, "following_count"):
            return user.following_count

        return user.following_relationships.count()

    def get_is_following(self, user):
        is_following = getattr(user, "is_following", None)

        if is_following is not None:
            return is_following

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return user.follower_relationships.filter(follower=request.user).exists()

    def get_follow_id(self, user):
        follow_id = getattr(user, "follow_id", None)

        if follow_id is not None:
            return follow_id

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return None

        follow = user.follower_relationships.filter(follower=request.user).first()
        return follow.id if follow else None


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


def token_pair_for(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "phone", "first_name", "last_name", "avatar", "is_email_verified", "is_phone_verified")
        read_only_fields = ("id", "is_email_verified", "is_phone_verified")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("email", "phone", "password", "first_name", "last_name")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Email or phone is required.")
        return attrs

    def create(self, validated_data):  # type: ignore[no-untyped-def]
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        user = authenticate(identifier=attrs["identifier"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        attrs["user"] = user
        return attrs


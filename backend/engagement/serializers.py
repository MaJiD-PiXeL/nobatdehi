from __future__ import annotations

from rest_framework import serializers

from .models import Favorite, Notification, Review


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("id", "status", "sent_at", "provider_response", "created_at", "updated_at")


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = "__all__"
        read_only_fields = ("id", "user", "created_at", "updated_at")


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ("id", "customer", "business", "employee", "service", "created_at", "updated_at", "response", "responded_at")


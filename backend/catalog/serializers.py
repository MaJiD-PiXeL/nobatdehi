from __future__ import annotations

from rest_framework import serializers

from .models import Service, ServiceCategory


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        business = attrs.get("business", getattr(self.instance, "business", None))
        category = attrs.get("category", getattr(self.instance, "category", None))
        branches = attrs.get("branches")
        if category and category.business_id != business.id:
            raise serializers.ValidationError({"category": "Category belongs to a different business."})
        if branches and any(branch.business_id != business.id for branch in branches):
            raise serializers.ValidationError({"branches": "Every branch must belong to this business."})
        return attrs


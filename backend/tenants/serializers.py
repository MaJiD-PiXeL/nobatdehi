from __future__ import annotations

from rest_framework import serializers

from .models import Branch, BranchWorkHour, Business, BusinessMember


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = (
            "id", "name", "slug", "description", "logo", "cover_image", "phone", "email", "address",
            "latitude", "longitude", "timezone", "cancellation_window_hours", "social_links", "is_active",
            "created_at",
        )
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):  # type: ignore[no-untyped-def]
        request = self.context["request"]
        business = Business.objects.create(owner=request.user, **validated_data)
        BusinessMember.objects.create(business=business, user=request.user, role=BusinessMember.Role.OWNER)
        return business


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_business(self, business: Business) -> Business:
        user = self.context["request"].user
        if not user.is_superuser and not user.business_memberships.filter(business=business, is_active=True).exists():
            raise serializers.ValidationError("You are not a member of this business.")
        return business


class BranchWorkHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchWorkHour
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if start >= end:
            raise serializers.ValidationError("End time must be later than start time.")
        return attrs


class BusinessMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessMember
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

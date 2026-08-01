from __future__ import annotations

from datetime import time

from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from catalog.models import Service
from workforce.models import Employee, EmployeeService, WorkSchedule

from .models import Branch, BranchWorkHour, Business, BusinessMember


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = (
            "id", "name", "slug", "description", "logo", "cover_image", "phone", "email", "address",
            "latitude", "longitude", "timezone", "cancellation_window_hours", "social_links", "is_active",
            "created_at",
        )
        read_only_fields = ("id", "slug", "created_at")

    def create(self, validated_data):  # type: ignore[no-untyped-def]
        request = self.context["request"]
        business = Business.objects.create(owner=request.user, **validated_data)
        BusinessMember.objects.create(business=business, user=request.user, role=BusinessMember.Role.OWNER)
        return business


class PublicBusinessSerializer(serializers.ModelSerializer):
    providers = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = ("id", "name", "slug", "description", "logo", "phone", "address", "timezone", "providers")

    def get_providers(self, business: Business) -> list[dict[str, str]]:
        return [
            {"name": employee.full_name, "specialty": employee.specialty}
            for employee in business.employees.filter(is_active=True).only("first_name", "last_name", "specialty")[:4]
        ]


class BusinessOnboardingSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=16, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    branch_name = serializers.CharField(max_length=160, default="شعبه اصلی")
    professional_first_name = serializers.CharField(max_length=100)
    professional_last_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    specialty = serializers.CharField(max_length=160, required=False, allow_blank=True)
    service_name = serializers.CharField(max_length=160)
    service_price = serializers.DecimalField(max_digits=12, decimal_places=0, min_value=0)
    service_duration_minutes = serializers.IntegerField(min_value=5, max_value=480, default=60)
    opens_at = serializers.TimeField(default=time(9, 0))
    closes_at = serializers.TimeField(default=time(17, 0))
    working_days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        min_length=1,
        default=[0, 1, 2, 3, 4, 5],
    )

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        if attrs["opens_at"] >= attrs["closes_at"]:
            raise serializers.ValidationError({"closes_at": "زمان پایان باید بعد از زمان شروع باشد."})
        attrs["working_days"] = sorted(set(attrs["working_days"]))
        return attrs

    @transaction.atomic
    def create(self, validated_data):  # type: ignore[no-untyped-def]
        request = self.context["request"]
        business = Business.objects.create(
            owner=request.user,
            name=validated_data["business_name"],
            description=validated_data.get("description", ""),
            phone=validated_data.get("phone", ""),
            address=validated_data.get("address", ""),
        )
        BusinessMember.objects.create(business=business, user=request.user, role=BusinessMember.Role.OWNER)

        branch_name = validated_data["branch_name"]
        branch = Branch.objects.create(
            business=business,
            name=branch_name,
            slug=slugify(branch_name, allow_unicode=True) or "main",
            phone=business.phone,
            address=business.address,
            timezone=business.timezone,
        )
        service = Service.objects.create(
            business=business,
            name=validated_data["service_name"],
            price=validated_data["service_price"],
            duration_minutes=validated_data["service_duration_minutes"],
        )
        service.branches.add(branch)

        employee = Employee.objects.create(
            business=business,
            first_name=validated_data["professional_first_name"],
            last_name=validated_data.get("professional_last_name", ""),
            specialty=validated_data.get("specialty", ""),
            phone=business.phone,
        )
        employee.branches.add(branch)
        EmployeeService.objects.create(employee=employee, service=service)

        for weekday in validated_data["working_days"]:
            BranchWorkHour.objects.create(
                branch=branch,
                weekday=weekday,
                starts_at=validated_data["opens_at"],
                ends_at=validated_data["closes_at"],
            )
            WorkSchedule.objects.create(
                employee=employee,
                branch=branch,
                weekday=weekday,
                starts_at=validated_data["opens_at"],
                ends_at=validated_data["closes_at"],
            )
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

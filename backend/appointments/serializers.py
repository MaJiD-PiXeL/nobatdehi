from __future__ import annotations

from rest_framework import serializers

from .models import Appointment, AppointmentStatusHistory, Customer
from .services import BookingService


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class AppointmentStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentStatusHistory
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = (
            "id", "business", "branch", "service", "employee", "customer", "customer_name", "customer_phone",
            "starts_at", "ends_at", "reserved_from", "reserved_until", "status", "tracking_code", "quoted_price",
            "discount_amount", "notes", "cancelled_at", "cancellation_reason", "created_at",
        )
        read_only_fields = ("id", "customer", "ends_at", "reserved_from", "reserved_until", "status", "tracking_code", "quoted_price", "discount_amount", "cancelled_at", "cancellation_reason", "created_at")

    def create(self, validated_data):  # type: ignore[no-untyped-def]
        request = self.context["request"]
        return BookingService.create_appointment(
            actor=request.user,
            business_id=validated_data.pop("business").id,
            branch_id=validated_data.pop("branch").id,
            service_id=validated_data.pop("service").id,
            employee_id=validated_data.pop("employee").id,
            starts_at=validated_data.pop("starts_at"),
            customer_name=validated_data.pop("customer_name"),
            customer_phone=validated_data.pop("customer_phone"),
            notes=validated_data.pop("notes", ""),
        )


class AvailabilityQuerySerializer(serializers.Serializer):
    branch_id = serializers.UUIDField()
    service_id = serializers.UUIDField()
    date = serializers.DateField()
    employee_id = serializers.UUIDField(required=False)


class CancelAppointmentSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)


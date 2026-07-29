from __future__ import annotations

from rest_framework import serializers

from .models import DiscountCode, Payment, Refund


class DiscountCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscountCode
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class PaymentSerializer(serializers.ModelSerializer):
    idempotency_key = serializers.UUIDField(required=False)

    class Meta:
        model = Payment
        fields = ("id", "appointment", "amount", "method", "status", "provider", "idempotency_key", "gateway_reference", "paid_at", "created_at")
        read_only_fields = ("id", "amount", "status", "provider", "gateway_reference", "paid_at", "created_at")


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "status")


class ApplyDiscountSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=40)


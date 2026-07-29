from __future__ import annotations

import secrets

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from appointments.models import Appointment
from common.permissions import member_business_ids
from tenants.views import TenantFilteredViewSet

from .models import DiscountCode, Payment, Refund
from .serializers import ApplyDiscountSerializer, DiscountCodeSerializer, PaymentSerializer, RefundSerializer
from .services import DiscountService, PaymentService


class DiscountCodeViewSet(TenantFilteredViewSet):
    queryset = DiscountCode.objects.select_related("business", "service", "branch")
    serializer_class = DiscountCodeSerializer


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        user = self.request.user
        queryset = Payment.objects.select_related("appointment", "appointment__customer")
        if user.is_superuser:
            return queryset
        return queryset.filter(appointment__business_id__in=member_business_ids(user)) | queryset.filter(appointment__customer__user=user)

    @action(detail=False, methods=["post"])
    def initiate(self, request):  # type: ignore[no-untyped-def]
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = serializer.validated_data["appointment"]
        is_member = request.user.is_superuser or request.user.business_memberships.filter(business=appointment.business, is_active=True).exists()
        if appointment.customer.user_id != request.user.id and not is_member:
            return Response({"detail": "You cannot pay for this appointment."}, status=status.HTTP_403_FORBIDDEN)
        payment = PaymentService.create_mock_payment(appointment=appointment, method=serializer.validated_data["method"], idempotency_key=serializer.validated_data.get("idempotency_key"))
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def mock_verify(self, request, pk=None):  # type: ignore[no-untyped-def]
        payment = self.get_object()
        payment = PaymentService.confirm_mock_payment(payment=payment, gateway_reference=f"MOCK-{secrets.token_hex(6).upper()}")
        return Response(PaymentSerializer(payment).data)


class RefundViewSet(TenantFilteredViewSet):
    queryset = Refund.objects.select_related("payment", "payment__appointment", "payment__appointment__business")
    serializer_class = RefundSerializer
    business_lookup = "payment__appointment__business_id"


class AppointmentDiscountViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path=r"appointments/(?P<appointment_id>[^/.]+)/apply")
    def apply(self, request, appointment_id=None):  # type: ignore[no-untyped-def]
        appointment = Appointment.objects.select_related("customer", "business").get(pk=appointment_id)
        if appointment.customer.user_id != request.user.id and not request.user.business_memberships.filter(business=appointment.business, is_active=True).exists() and not request.user.is_superuser:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        serializer = ApplyDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = DiscountService.apply(code=serializer.validated_data["code"], appointment=appointment)
        return Response({"discount_amount": amount})

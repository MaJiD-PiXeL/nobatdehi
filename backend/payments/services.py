from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from appointments.models import Appointment, AppointmentStatusHistory

from .models import DiscountCode, DiscountRedemption, Payment


class DiscountService:
    @staticmethod
    @transaction.atomic
    def apply(*, code: str, appointment: Appointment) -> Decimal:
        discount = DiscountCode.objects.select_for_update().filter(business=appointment.business, code__iexact=code, is_active=True).first()
        now = timezone.now()
        if not discount or not (discount.starts_at <= now <= discount.ends_at):
            raise ValidationError({"code": "Discount code is invalid or expired."})
        if discount.service_id and discount.service_id != appointment.service_id:
            raise ValidationError({"code": "This code is not valid for the selected service."})
        if discount.branch_id and discount.branch_id != appointment.branch_id:
            raise ValidationError({"code": "This code is not valid for the selected branch."})
        if appointment.quoted_price < discount.minimum_purchase:
            raise ValidationError({"code": "Minimum purchase amount was not met."})
        used = discount.redemptions.count()
        customer_used = discount.redemptions.filter(customer=appointment.customer).count()
        if (discount.usage_limit is not None and used >= discount.usage_limit) or customer_used >= discount.per_customer_limit:
            raise ValidationError({"code": "Usage limit has been reached."})
        if discount.new_customers_only and appointment.customer.appointments.exclude(id=appointment.id).exists():
            raise ValidationError({"code": "This code is only for new customers."})
        amount = (appointment.quoted_price * discount.value / Decimal("100")) if discount.kind == DiscountCode.Kind.PERCENT else discount.value
        amount = min(amount, appointment.quoted_price)
        appointment.discount_amount = amount
        appointment.save(update_fields=["discount_amount", "updated_at"])
        DiscountRedemption.objects.create(discount_code=discount, customer=appointment.customer, appointment=appointment, amount=amount)
        return amount


class PaymentService:
    @staticmethod
    @transaction.atomic
    def create_mock_payment(*, appointment: Appointment, method: str, idempotency_key=None) -> Payment:
        if idempotency_key:
            existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing
        due = appointment.service.deposit_amount if method == Payment.Method.DEPOSIT else appointment.quoted_price - appointment.discount_amount
        if due < 0:
            raise ValidationError({"amount": "Payment amount cannot be negative."})
        values = {"appointment": appointment, "amount": due, "method": method, "status": Payment.Status.PENDING}
        if idempotency_key:
            values["idempotency_key"] = idempotency_key
        return Payment.objects.create(**values)

    @staticmethod
    @transaction.atomic
    def confirm_mock_payment(*, payment: Payment, gateway_reference: str) -> Payment:
        payment = Payment.objects.select_for_update().select_related("appointment").get(pk=payment.pk)
        if payment.status == Payment.Status.SUCCEEDED:
            return payment
        if payment.status not in {Payment.Status.INITIATED, Payment.Status.PENDING}:
            raise ValidationError({"status": "This payment cannot be confirmed."})
        payment.status = Payment.Status.SUCCEEDED
        payment.gateway_reference = gateway_reference
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "gateway_reference", "paid_at", "updated_at"])
        if payment.appointment.status == Appointment.Status.PENDING_PAYMENT:
            previous = payment.appointment.status
            payment.appointment.status = Appointment.Status.CONFIRMED
            payment.appointment.save(update_fields=["status", "updated_at"])
            AppointmentStatusHistory.objects.create(appointment=payment.appointment, from_status=previous, to_status=Appointment.Status.CONFIRMED)
        return payment

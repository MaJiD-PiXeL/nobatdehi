from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from common.models import UUIDTimeStampedModel
from tenants.models import Branch, Business


class DiscountCode(UUIDTimeStampedModel):
    class Kind(models.TextChoices):
        PERCENT = "percent", "Percent"
        FIXED = "fixed", "Fixed amount"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="discount_codes")
    code = models.CharField(max_length=40)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    value = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("0"))])
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    per_customer_limit = models.PositiveSmallIntegerField(default=1)
    minimum_purchase = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    service = models.ForeignKey("catalog.Service", on_delete=models.SET_NULL, null=True, blank=True, related_name="discount_codes")
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="discount_codes")
    new_customers_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "code"], name="unique_discount_code_per_business")]
        indexes = [models.Index(fields=["business", "code", "is_active"]), models.Index(fields=["starts_at", "ends_at"])]

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.starts_at >= self.ends_at:
            raise ValidationError("Discount end must be later than start.")
        if self.kind == self.Kind.PERCENT and self.value > 100:
            raise ValidationError({"value": "Percentage cannot exceed 100."})
        if self.service_id and self.service.business_id != self.business_id:
            raise ValidationError({"service": "Service belongs to another business."})
        if self.branch_id and self.branch.business_id != self.business_id:
            raise ValidationError({"branch": "Branch belongs to another business."})


class DiscountRedemption(UUIDTimeStampedModel):
    discount_code = models.ForeignKey(DiscountCode, on_delete=models.PROTECT, related_name="redemptions")
    customer = models.ForeignKey("appointments.Customer", on_delete=models.PROTECT, related_name="discount_redemptions")
    appointment = models.OneToOneField("appointments.Appointment", on_delete=models.CASCADE, related_name="discount_redemption")
    amount = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        indexes = [models.Index(fields=["discount_code", "customer"])]


class Payment(UUIDTimeStampedModel):
    class Method(models.TextChoices):
        FULL = "full", "Full payment"
        DEPOSIT = "deposit", "Deposit"
        IN_PERSON = "in_person", "In person"

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    appointment = models.ForeignKey("appointments.Appointment", on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("0"))])
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    provider = models.CharField(max_length=50, default="mock")
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    gateway_reference = models.CharField(max_length=100, null=True, blank=True, unique=True)
    callback_payload = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["appointment", "status"]), models.Index(fields=["provider", "status"])]


class Refund(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="refunds")
    amount = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("0"))])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    provider_reference = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [models.Index(fields=["payment", "status"])]


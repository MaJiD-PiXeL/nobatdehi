from __future__ import annotations

import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from common.models import UUIDTimeStampedModel
from tenants.models import Branch, Business


class Customer(UUIDTimeStampedModel):
    """A tenant-local customer profile; users may be customers of many tenants."""

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="customers")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="customer_profiles")
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=16)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)
    is_blocked = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "user"], name="unique_customer_profile_per_business")]
        indexes = [models.Index(fields=["business", "phone"]), models.Index(fields=["business", "user"])]


class Appointment(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PENDING_CONFIRMATION = "pending_confirmation", "Pending confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED_BY_CUSTOMER = "cancelled_by_customer", "Cancelled by customer"
        CANCELLED_BY_BUSINESS = "cancelled_by_business", "Cancelled by business"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No show"
        REFUNDED = "refunded", "Refunded"

    BLOCKING_STATUSES = (Status.PENDING_PAYMENT, Status.PENDING_CONFIRMATION, Status.CONFIRMED)

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="appointments")
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="appointments")
    service = models.ForeignKey("catalog.Service", on_delete=models.PROTECT, related_name="appointments")
    employee = models.ForeignKey("workforce.Employee", on_delete=models.PROTECT, related_name="appointments")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="appointments")
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=16)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reserved_from = models.DateTimeField(help_text="Start including the pre-service buffer.")
    reserved_until = models.DateTimeField(help_text="End including the post-service buffer.")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING_CONFIRMATION)
    tracking_code = models.CharField(max_length=14, unique=True, editable=False)
    quoted_price = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("0"))])
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(Decimal("0"))])
    notes = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["business", "starts_at", "status"]),
            models.Index(fields=["employee", "reserved_from", "reserved_until"]),
            models.Index(fields=["customer", "starts_at"]),
        ]
        ordering = ["starts_at"]

    def save(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        if not self.tracking_code:
            self.tracking_code = f"NB-{secrets.token_hex(5).upper()}"
        super().save(*args, **kwargs)

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        errors: dict[str, str] = {}
        if self.starts_at >= self.ends_at:
            errors["ends_at"] = "End must be later than start."
        if self.reserved_from > self.starts_at or self.reserved_until < self.ends_at:
            errors["reserved_from"] = "Reserved interval must include the appointment interval."
        for field, value in (("branch", self.branch), ("service", self.service), ("employee", self.employee), ("customer", self.customer)):
            if value.business_id != self.business_id:
                errors[field] = "Related object belongs to another business."
        if errors:
            raise ValidationError(errors)


class AppointmentStatusHistory(UUIDTimeStampedModel):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=32, choices=Appointment.Status.choices, blank=True)
    to_status = models.CharField(max_length=32, choices=Appointment.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointment_status_changes")
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["appointment", "created_at"])]


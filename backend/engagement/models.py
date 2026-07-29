from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import UUIDTimeStampedModel
from tenants.models import Business


class Notification(UUIDTimeStampedModel):
    class Channel(models.TextChoices):
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"
        IN_APP = "in_app", "In-app"
        TELEGRAM = "telegram", "Telegram"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    appointment = models.ForeignKey("appointments.Appointment", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    channel = models.CharField(max_length=20, choices=Channel.choices)
    title = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "read_at", "created_at"]), models.Index(fields=["status", "scheduled_for"])]


class Review(UUIDTimeStampedModel):
    appointment = models.OneToOneField("appointments.Appointment", on_delete=models.CASCADE, related_name="review")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey("appointments.Customer", on_delete=models.CASCADE, related_name="reviews")
    employee = models.ForeignKey("workforce.Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    service = models.ForeignKey("catalog.Service", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["business", "rating", "is_visible"])]


class Favorite(UUIDTimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "business"], name="unique_user_favorite")]


class AuditLog(UUIDTimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=100)
    object_id = models.UUIDField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["business", "created_at"]), models.Index(fields=["object_type", "object_id"])]


class SubscriptionPlan(UUIDTimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=0)
    max_branches = models.PositiveSmallIntegerField(default=1)
    max_employees = models.PositiveSmallIntegerField(default=3)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)


class BusinessSubscription(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        TRIAL = "trial", "Trial"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELLED = "cancelled", "Cancelled"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIAL)
    auto_renew = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["business", "status", "ends_at"])]


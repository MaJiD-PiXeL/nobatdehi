from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils.text import slugify

from common.models import UUIDTimeStampedModel


class Business(UUIDTimeStampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_businesses")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="businesses/logos/", null=True, blank=True)
    cover_image = models.ImageField(upload_to="businesses/covers/", null=True, blank=True)
    phone = models.CharField(max_length=16, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Tehran")
    cancellation_window_hours = models.PositiveSmallIntegerField(default=24, validators=[MaxValueValidator(720)])
    social_links = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["slug", "is_active"]), models.Index(fields=["owner", "is_active"])]

    def save(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Branch(UUIDTimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160)
    phone = models.CharField(max_length=16, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Tehran")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "slug"], name="unique_branch_slug_per_business")]
        indexes = [models.Index(fields=["business", "is_active"])]

    def __str__(self) -> str:
        return f"{self.business.name} — {self.name}"


class BusinessMember(UUIDTimeStampedModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        BRANCH_MANAGER = "branch_manager", "Branch manager"
        EMPLOYEE = "employee", "Employee"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_memberships")
    role = models.CharField(max_length=30, choices=Role.choices)
    branches = models.ManyToManyField(Branch, blank=True, related_name="authorized_members")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "user"], name="unique_business_membership")]
        indexes = [models.Index(fields=["user", "is_active"]), models.Index(fields=["business", "role", "is_active"])]


class BranchWorkHour(UUIDTimeStampedModel):
    """Weekly open hours. Overnight shifts are intentionally split into two rows."""

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="work_hours")
    weekday = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])
    starts_at = models.TimeField()
    ends_at = models.TimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["branch", "weekday", "starts_at"], name="unique_branch_open_interval")]
        ordering = ["weekday", "starts_at"]

    def clean(self) -> None:
        if self.starts_at >= self.ends_at:
            from django.core.exceptions import ValidationError

            raise ValidationError("End time must be later than start time.")


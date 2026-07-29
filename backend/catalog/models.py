from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from common.models import UUIDTimeStampedModel
from tenants.models import Branch, Business


class ServiceCategory(UUIDTimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="service_categories")
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "name"], name="unique_service_category_name")]
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["business", "is_active"])]


class Service(UUIDTimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="services")
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="services")
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("0"))])
    duration_minutes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    buffer_before_minutes = models.PositiveSmallIntegerField(default=0)
    buffer_after_minutes = models.PositiveSmallIntegerField(default=0)
    image = models.ImageField(upload_to="services/", null=True, blank=True)
    requires_deposit = models.BooleanField(default=False)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(Decimal("0"))])
    max_parallel_bookings = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    branches = models.ManyToManyField(Branch, related_name="services")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "name"], name="unique_service_name_per_business")]
        indexes = [models.Index(fields=["business", "is_active"]), models.Index(fields=["business", "category"])]

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.category_id and self.category.business_id != self.business_id:
            raise ValidationError({"category": "Category must belong to the service business."})
        if self.requires_deposit and not self.deposit_amount:
            raise ValidationError({"deposit_amount": "Deposit amount is required."})


from __future__ import annotations

import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from common.models import UUIDTimeStampedModel

from .managers import UserManager

phone_validator = RegexValidator(regex=r"^\+?[0-9]{10,15}$", message="Enter a valid phone number.")


class User(AbstractBaseUser, PermissionsMixin, UUIDTimeStampedModel):
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=16, unique=True, null=True, blank=True, validators=[phone_validator])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(auto_now_add=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        indexes = [models.Index(fields=["phone"]), models.Index(fields=["email"])]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return self.email or self.phone or str(self.pk)


class OTPChallenge(UUIDTimeStampedModel):
    """Short-lived, one-time verification code. Store only its hash in production."""

    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"
        VERIFY_PHONE = "verify_phone", "Verify phone"
        VERIFY_EMAIL = "verify_email", "Verify email"
        PASSWORD_RESET = "password_reset", "Password reset"

    destination = models.CharField(max_length=254)
    code = models.CharField(max_length=8)
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["destination", "purpose", "expires_at"])]

    @classmethod
    def issue(cls, destination: str, purpose: str) -> "OTPChallenge":
        return cls.objects.create(
            destination=destination,
            purpose=purpose,
            code=f"{secrets.randbelow(1_000_000):06d}",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

    def verify(self, code: str) -> bool:
        self.attempts += 1
        valid = self.consumed_at is None and self.expires_at >= timezone.now() and self.attempts <= 5 and secrets.compare_digest(self.code, code)
        if valid:
            self.consumed_at = timezone.now()
        self.save(update_fields=["attempts", "consumed_at", "updated_at"])
        return valid


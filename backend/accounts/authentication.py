from __future__ import annotations

from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate with the user's verified email or mobile number."""

    def authenticate(self, request, username=None, password=None, **kwargs):  # type: ignore[no-untyped-def]
        identifier = kwargs.get("identifier") or username
        if not identifier or not password:
            return None
        try:
            user = User.objects.get(Q(email__iexact=identifier) | Q(phone=identifier))
        except User.DoesNotExist:
            User().set_password(password)  # Timing-safe dummy hash.
            return None
        return user if user.check_password(password) and self.user_can_authenticate(user) else None


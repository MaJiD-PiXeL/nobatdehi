from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from appointments.tests.test_booking_service import BookingServiceTests
from payments.models import DiscountCode
from payments.services import DiscountService


class DiscountServiceTests(BookingServiceTests):
    def test_percent_discount_is_applied_once(self) -> None:
        appointment = self._book()
        now = timezone.now()
        code = DiscountCode.objects.create(
            business=self.business,
            code="WELCOME20",
            kind=DiscountCode.Kind.PERCENT,
            value=20,
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(days=1),
            usage_limit=1,
        )
        discount = DiscountService.apply(code=code.code, appointment=appointment)
        appointment.refresh_from_db()
        self.assertEqual(discount, 100_000)
        self.assertEqual(appointment.discount_amount, 100_000)


from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from catalog.models import Service
from tenants.models import Branch, BranchWorkHour, Business, BusinessMember
from workforce.models import Employee, EmployeeService, WorkSchedule

from appointments.models import Appointment
from appointments.services import BookingService, SlotUnavailable, available_slots


class BookingServiceTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="customer@example.test", password="correct-horse-battery-staple")
        self.owner = User.objects.create_user(email="owner@example.test", password="correct-horse-battery-staple")
        self.business = Business.objects.create(owner=self.owner, name="مرکز سلامت", slug="health-center", cancellation_window_hours=1)
        BusinessMember.objects.create(business=self.business, user=self.owner, role=BusinessMember.Role.OWNER)
        self.branch = Branch.objects.create(business=self.business, name="مرکزی", slug="central")
        self.service = Service.objects.create(business=self.business, name="مشاوره", price=500_000, duration_minutes=60)
        self.service.branches.add(self.branch)
        self.employee = Employee.objects.create(business=self.business, first_name="نیلوفر", last_name="احمدی")
        self.employee.branches.add(self.branch)
        EmployeeService.objects.create(employee=self.employee, service=self.service)
        self.starts_at = self._future_at(10)
        BranchWorkHour.objects.create(branch=self.branch, weekday=self.starts_at.weekday(), starts_at=time(9), ends_at=time(17))
        WorkSchedule.objects.create(employee=self.employee, branch=self.branch, weekday=self.starts_at.weekday(), starts_at=time(9), ends_at=time(17))

    @staticmethod
    def _future_at(hour: int):
        day = timezone.localdate() + timedelta(days=3)
        return timezone.make_aware(datetime.combine(day, time(hour)), ZoneInfo("Asia/Tehran"))

    def _book(self, starts_at=None):
        return BookingService.create_appointment(
            actor=self.user,
            business_id=self.business.id,
            branch_id=self.branch.id,
            service_id=self.service.id,
            employee_id=self.employee.id,
            starts_at=starts_at or self.starts_at,
            customer_name="سارا رضایی",
            customer_phone="09120000000",
        )

    def test_available_slots_are_calculated_in_backend(self) -> None:
        slots = available_slots(branch=self.branch, service=self.service, day=self.starts_at.date(), employee=self.employee)
        starts = {slot.starts_at for slot in slots}
        self.assertIn(self.starts_at, starts)

    def test_overlapping_appointment_is_rejected(self) -> None:
        appointment = self._book()
        self.assertEqual(appointment.status, Appointment.Status.CONFIRMED)
        with self.assertRaises(SlotUnavailable):
            self._book(self.starts_at + timedelta(minutes=30))

    def test_cancellation_releases_the_slot(self) -> None:
        appointment = self._book()
        BookingService.cancel_appointment(appointment=appointment, actor=self.user, by_business=False)
        replacement = self._book()
        self.assertEqual(replacement.status, Appointment.Status.CONFIRMED)


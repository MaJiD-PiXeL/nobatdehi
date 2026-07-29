from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from catalog.models import Service
from tenants.models import Branch, BranchWorkHour
from workforce.models import Employee, EmployeeLeave, EmployeeService, Holiday, WorkSchedule

from .models import Appointment, AppointmentStatusHistory, Customer


class SlotUnavailable(APIException):
    status_code = 409
    default_detail = "The selected time slot is no longer available."
    default_code = "slot_unavailable"


@dataclass(frozen=True)
class Slot:
    employee_id: str
    starts_at: datetime
    ends_at: datetime


def overlap(left_start: datetime, left_end: datetime, right_start: datetime, right_end: datetime) -> bool:
    return left_start < right_end and left_end > right_start


def appointment_bounds(service: Service, starts_at: datetime) -> tuple[datetime, datetime, datetime]:
    ends_at = starts_at + timedelta(minutes=service.duration_minutes)
    reserved_from = starts_at - timedelta(minutes=service.buffer_before_minutes)
    reserved_until = ends_at + timedelta(minutes=service.buffer_after_minutes)
    return ends_at, reserved_from, reserved_until


def _at(day: date, value: time, zone: ZoneInfo) -> datetime:
    return timezone.make_aware(datetime.combine(day, value), zone)


def _schedule_allows(employee: Employee, branch: Branch, reserved_from: datetime, reserved_until: datetime) -> bool:
    """Ensure the buffered appointment fits both staff and branch working intervals."""
    if reserved_from.date() != reserved_until.date():
        return False
    weekday = reserved_from.weekday()
    schedules = WorkSchedule.objects.filter(employee=employee, branch=branch, weekday=weekday, is_active=True).prefetch_related("breaks")
    branch_hours = BranchWorkHour.objects.filter(branch=branch, weekday=weekday)
    for schedule in schedules:
        zone = ZoneInfo(branch.timezone)
        schedule_start, schedule_end = _at(reserved_from.date(), schedule.starts_at, zone), _at(reserved_from.date(), schedule.ends_at, zone)
        if not (schedule_start <= reserved_from and reserved_until <= schedule_end):
            continue
        if any(overlap(reserved_from, reserved_until, _at(reserved_from.date(), pause.starts_at, zone), _at(reserved_from.date(), pause.ends_at, zone)) for pause in schedule.breaks.all()):
            continue
        if any(_at(reserved_from.date(), hours.starts_at, zone) <= reserved_from and reserved_until <= _at(reserved_from.date(), hours.ends_at, zone) for hours in branch_hours):
            return True
    return False


def _is_holiday_or_leave(employee: Employee, branch: Branch, reserved_from: datetime, reserved_until: datetime) -> bool:
    if Holiday.objects.filter(business=employee.business, date=reserved_from.date()).filter(Q(branch__isnull=True) | Q(branch=branch)).exists():
        return True
    return EmployeeLeave.objects.filter(employee=employee, starts_at__lt=reserved_until, ends_at__gt=reserved_from).exists()


def slot_is_available(employee: Employee, branch: Branch, service: Service, starts_at: datetime, *, lock: bool = False) -> bool:
    starts_at = starts_at.astimezone(ZoneInfo(branch.timezone))
    ends_at, reserved_from, reserved_until = appointment_bounds(service, starts_at)
    if starts_at <= timezone.now() or not employee.is_active or not service.is_active or not branch.is_active:
        return False
    if not employee.branches.filter(id=branch.id).exists() or not EmployeeService.objects.filter(employee=employee, service=service, is_active=True).exists():
        return False
    if _is_holiday_or_leave(employee, branch, reserved_from, reserved_until) or not _schedule_allows(employee, branch, reserved_from, reserved_until):
        return False
    appointments = Appointment.objects.filter(
        employee=employee,
        status__in=Appointment.BLOCKING_STATUSES,
        reserved_from__lt=reserved_until,
        reserved_until__gt=reserved_from,
    )
    if lock:
        appointments = appointments.select_for_update()
    return not appointments.exists()


class BookingService:
    """Transactional use case; views never persist appointments directly."""

    @staticmethod
    @transaction.atomic
    def create_appointment(
        *,
        actor,
        business_id,
        branch_id,
        service_id,
        employee_id,
        starts_at: datetime,
        customer_name: str,
        customer_phone: str,
        customer_email: str = "",
        notes: str = "",
    ) -> Appointment:
        if timezone.is_naive(starts_at):
            raise ValidationError({"starts_at": "An ISO-8601 timezone-aware timestamp is required."})
        branch = Branch.objects.select_related("business").get(id=branch_id, business_id=business_id)
        service = Service.objects.select_related("business").get(id=service_id, business_id=business_id)
        employee = Employee.objects.select_for_update().get(id=employee_id, business_id=business_id)
        if not service.branches.filter(id=branch.id).exists():
            raise ValidationError({"branch_id": "This service is not offered at the selected branch."})
        if not slot_is_available(employee, branch, service, starts_at, lock=True):
            raise SlotUnavailable()

        customer, _ = Customer.objects.update_or_create(
            business_id=business_id,
            user=actor if actor and actor.is_authenticated else None,
            defaults={"full_name": customer_name, "phone": customer_phone, "email": customer_email},
        )
        if customer.is_blocked:
            raise ValidationError({"customer": "This customer is blocked by this business."})
        ends_at, reserved_from, reserved_until = appointment_bounds(service, starts_at)
        status = Appointment.Status.PENDING_PAYMENT if service.requires_deposit else Appointment.Status.CONFIRMED
        try:
            appointment = Appointment.objects.create(
                business_id=business_id,
                branch=branch,
                service=service,
                employee=employee,
                customer=customer,
                customer_name=customer_name,
                customer_phone=customer_phone,
                starts_at=starts_at,
                ends_at=ends_at,
                reserved_from=reserved_from,
                reserved_until=reserved_until,
                quoted_price=service.price,
                status=status,
                notes=notes,
            )
        except IntegrityError as exc:
            # Covers the PostgreSQL exclusion constraint once its migration is applied.
            raise SlotUnavailable() from exc
        AppointmentStatusHistory.objects.create(appointment=appointment, to_status=status, changed_by=actor)
        return appointment

    @staticmethod
    @transaction.atomic
    def cancel_appointment(*, appointment: Appointment, actor, by_business: bool, reason: str = "") -> Appointment:
        appointment = Appointment.objects.select_for_update().select_related("business").get(pk=appointment.pk)
        if appointment.status not in Appointment.BLOCKING_STATUSES:
            raise ValidationError({"status": "Only active appointments can be cancelled."})
        if not by_business:
            deadline = appointment.starts_at - timedelta(hours=appointment.business.cancellation_window_hours)
            if timezone.now() > deadline:
                raise ValidationError({"status": "The cancellation deadline has passed."})
        previous = appointment.status
        appointment.status = Appointment.Status.CANCELLED_BY_BUSINESS if by_business else Appointment.Status.CANCELLED_BY_CUSTOMER
        appointment.cancelled_at = timezone.now()
        appointment.cancellation_reason = reason
        appointment.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
        AppointmentStatusHistory.objects.create(appointment=appointment, from_status=previous, to_status=appointment.status, changed_by=actor, note=reason)
        return appointment


def available_slots(*, branch: Branch, service: Service, day: date, employee: Employee | None = None, interval_minutes: int = 15) -> list[Slot]:
    """Compute displayed slots in the backend. Availability is rechecked at booking time."""
    if branch.business_id != service.business_id:
        return []
    employees = Employee.objects.filter(business=branch.business, is_active=True, branches=branch).distinct()
    if employee:
        employees = employees.filter(id=employee.id)
    zone = ZoneInfo(branch.timezone)
    results: list[Slot] = []
    for candidate in employees:
        schedules = WorkSchedule.objects.filter(employee=candidate, branch=branch, weekday=day.weekday(), is_active=True)
        for schedule in schedules:
            cursor = _at(day, schedule.starts_at, zone) + timedelta(minutes=service.buffer_before_minutes)
            latest_start = _at(day, schedule.ends_at, zone) - timedelta(minutes=service.duration_minutes + service.buffer_after_minutes)
            while cursor <= latest_start:
                if slot_is_available(candidate, branch, service, cursor):
                    end, _, _ = appointment_bounds(service, cursor)
                    results.append(Slot(employee_id=str(candidate.id), starts_at=cursor, ends_at=end))
                cursor += timedelta(minutes=interval_minutes)
    return sorted(results, key=lambda slot: (slot.starts_at, slot.employee_id))

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from common.models import UUIDTimeStampedModel
from tenants.models import Branch, Business


class Employee(UUIDTimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="employees")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="employee_profiles")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=16, blank=True)
    email = models.EmailField(blank=True)
    avatar = models.ImageField(upload_to="employees/", null=True, blank=True)
    specialty = models.CharField(max_length=160, blank=True)
    branches = models.ManyToManyField(Branch, related_name="employees")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["business", "is_active"]), models.Index(fields=["business", "phone"])]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self) -> str:
        return self.full_name


class EmployeeService(UUIDTimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employee_services")
    service = models.ForeignKey("catalog.Service", on_delete=models.CASCADE, related_name="service_employees")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["employee", "service"], name="unique_employee_service")]
        indexes = [models.Index(fields=["service", "is_active"])]

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.employee.business_id != self.service.business_id:
            raise ValidationError("Employee and service must belong to the same business.")


class WorkSchedule(UUIDTimeStampedModel):
    """A weekly availability interval for a staff member at one branch."""

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="work_schedules")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="employee_schedules")
    weekday = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["employee", "branch", "weekday", "starts_at"], name="unique_employee_work_interval")]
        ordering = ["weekday", "starts_at"]
        indexes = [models.Index(fields=["employee", "branch", "weekday", "is_active"])]

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.starts_at >= self.ends_at:
            raise ValidationError("End time must be later than start time.")
        if self.employee.business_id != self.branch.business_id:
            raise ValidationError("Employee and branch must belong to the same business.")


class BreakTime(UUIDTimeStampedModel):
    work_schedule = models.ForeignKey(WorkSchedule, on_delete=models.CASCADE, related_name="breaks")
    starts_at = models.TimeField()
    ends_at = models.TimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["work_schedule", "starts_at"], name="unique_schedule_break_start")]
        ordering = ["starts_at"]

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.starts_at >= self.ends_at:
            raise ValidationError("Break end must be later than start.")
        if self.starts_at < self.work_schedule.starts_at or self.ends_at > self.work_schedule.ends_at:
            raise ValidationError("Break must fall within the work schedule.")


class Holiday(UUIDTimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="holidays")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="holidays", null=True, blank=True)
    date = models.DateField()
    title = models.CharField(max_length=160)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "branch", "date"], name="unique_holiday_scope_date")]
        indexes = [models.Index(fields=["business", "date"])]

    def clean(self) -> None:
        from django.core.exceptions import ValidationError

        if self.branch_id and self.branch.business_id != self.business_id:
            raise ValidationError("Branch must belong to the holiday business.")


class EmployeeLeave(UUIDTimeStampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=250, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_leaves")

    class Meta:
        indexes = [models.Index(fields=["employee", "starts_at", "ends_at"])]

    def clean(self) -> None:
        if self.starts_at >= self.ends_at:
            from django.core.exceptions import ValidationError

            raise ValidationError("Leave end must be later than start.")

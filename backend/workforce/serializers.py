from __future__ import annotations

from rest_framework import serializers

from .models import BreakTime, Employee, EmployeeLeave, EmployeeService, Holiday, WorkSchedule


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        business = attrs.get("business", getattr(self.instance, "business", None))
        branches = attrs.get("branches")
        if branches and any(branch.business_id != business.id for branch in branches):
            raise serializers.ValidationError({"branches": "Every branch must belong to this business."})
        return attrs


class EmployeeServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeService
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        employee = attrs.get("employee", getattr(self.instance, "employee", None))
        service = attrs.get("service", getattr(self.instance, "service", None))
        if employee and service and employee.business_id != service.business_id:
            raise serializers.ValidationError("Employee and service must share a business.")
        return attrs


class WorkScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkSchedule
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        employee = attrs.get("employee", getattr(self.instance, "employee", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if employee and branch and employee.business_id != branch.business_id:
            raise serializers.ValidationError("Employee and branch must share a business.")
        if attrs.get("starts_at", getattr(self.instance, "starts_at", None)) >= attrs.get("ends_at", getattr(self.instance, "ends_at", None)):
            raise serializers.ValidationError("End time must be later than start time.")
        return attrs


class BreakTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreakTime
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if start >= end:
            raise serializers.ValidationError("Break end must be later than start.")
        return attrs


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        business = attrs.get("business", getattr(self.instance, "business", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if branch and branch.business_id != business.id:
            raise serializers.ValidationError({"branch": "Branch belongs to a different business."})
        return attrs


class EmployeeLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeLeave
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):  # type: ignore[no-untyped-def]
        start = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if start >= end:
            raise serializers.ValidationError("Leave end must be later than start.")
        return attrs

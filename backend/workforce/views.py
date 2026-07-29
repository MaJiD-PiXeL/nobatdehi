from tenants.views import TenantFilteredViewSet

from .models import BreakTime, Employee, EmployeeLeave, EmployeeService, Holiday, WorkSchedule
from .serializers import BreakTimeSerializer, EmployeeLeaveSerializer, EmployeeSerializer, EmployeeServiceSerializer, HolidaySerializer, WorkScheduleSerializer


class EmployeeViewSet(TenantFilteredViewSet):
    queryset = Employee.objects.select_related("business", "user").prefetch_related("branches")
    serializer_class = EmployeeSerializer


class EmployeeServiceViewSet(TenantFilteredViewSet):
    queryset = EmployeeService.objects.select_related("employee", "employee__business", "service")
    serializer_class = EmployeeServiceSerializer
    business_lookup = "employee__business_id"


class WorkScheduleViewSet(TenantFilteredViewSet):
    queryset = WorkSchedule.objects.select_related("employee", "employee__business", "branch")
    serializer_class = WorkScheduleSerializer
    business_lookup = "employee__business_id"


class BreakTimeViewSet(TenantFilteredViewSet):
    queryset = BreakTime.objects.select_related("work_schedule", "work_schedule__employee", "work_schedule__employee__business")
    serializer_class = BreakTimeSerializer
    business_lookup = "work_schedule__employee__business_id"


class HolidayViewSet(TenantFilteredViewSet):
    queryset = Holiday.objects.select_related("business", "branch")
    serializer_class = HolidaySerializer


class EmployeeLeaveViewSet(TenantFilteredViewSet):
    queryset = EmployeeLeave.objects.select_related("employee", "employee__business", "approved_by")
    serializer_class = EmployeeLeaveSerializer
    business_lookup = "employee__business_id"


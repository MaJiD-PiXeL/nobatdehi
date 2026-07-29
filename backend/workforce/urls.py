from rest_framework.routers import DefaultRouter

from .views import BreakTimeViewSet, EmployeeLeaveViewSet, EmployeeServiceViewSet, EmployeeViewSet, HolidayViewSet, WorkScheduleViewSet

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")
router.register("employee-services", EmployeeServiceViewSet, basename="employee-service")
router.register("work-schedules", WorkScheduleViewSet, basename="work-schedule")
router.register("break-times", BreakTimeViewSet, basename="break-time")
router.register("holidays", HolidayViewSet, basename="holiday")
router.register("employee-leaves", EmployeeLeaveViewSet, basename="employee-leave")

urlpatterns = router.urls


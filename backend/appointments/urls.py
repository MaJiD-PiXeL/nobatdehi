from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AppointmentStatusHistoryViewSet, AppointmentViewSet, AvailabilityView, CustomerViewSet

router = DefaultRouter()
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register("customers", CustomerViewSet, basename="customer")
router.register("appointment-status-history", AppointmentStatusHistoryViewSet, basename="appointment-status-history")

urlpatterns = [path("availability/", AvailabilityView.as_view(), name="availability")] + router.urls


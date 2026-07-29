from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Service
from common.permissions import member_business_ids
from tenants.models import Branch
from workforce.models import Employee

from .models import Appointment, AppointmentStatusHistory, Customer
from .serializers import AppointmentSerializer, AppointmentStatusHistorySerializer, AvailabilityQuerySerializer, CancelAppointmentSerializer, CustomerSerializer
from .services import BookingService, available_slots


class AvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):  # type: ignore[no-untyped-def]
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        branch = get_object_or_404(Branch.objects.select_related("business"), id=data["branch_id"], is_active=True, business__is_active=True)
        service = get_object_or_404(Service, id=data["service_id"], business=branch.business, is_active=True, branches=branch)
        employee = None
        if data.get("employee_id"):
            employee = get_object_or_404(Employee, id=data["employee_id"], business=branch.business, is_active=True)
        slots = available_slots(branch=branch, service=service, day=data["date"], employee=employee)
        return Response({"slots": [{"employee_id": slot.employee_id, "starts_at": slot.starts_at, "ends_at": slot.ends_at} for slot in slots]})


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):  # type: ignore[no-untyped-def]
        user = self.request.user
        queryset = Appointment.objects.select_related("business", "branch", "service", "employee", "customer")
        if user.is_superuser:
            return queryset
        return queryset.filter(Q(business_id__in=member_business_ids(user)) | Q(customer__user=user)).distinct()

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):  # type: ignore[no-untyped-def]
        appointment = self.get_object()
        serializer = CancelAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_member = request.user.business_memberships.filter(business=appointment.business, is_active=True).exists() or request.user.is_superuser
        cancelled = BookingService.cancel_appointment(appointment=appointment, actor=request.user, by_business=is_member, reason=serializer.validated_data.get("reason", ""))
        return Response(self.get_serializer(cancelled).data)


class CustomerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CustomerSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        if self.request.user.is_superuser:
            return Customer.objects.all()
        return Customer.objects.filter(business_id__in=member_business_ids(self.request.user))


class AppointmentStatusHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentStatusHistorySerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        if self.request.user.is_superuser:
            return AppointmentStatusHistory.objects.select_related("appointment")
        return AppointmentStatusHistory.objects.select_related("appointment").filter(appointment__business_id__in=member_business_ids(self.request.user))

from __future__ import annotations

from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from appointments.models import Appointment
from common.permissions import member_business_ids

from .models import Favorite, Notification, Review
from .serializers import FavoriteSerializer, NotificationSerializer, ReviewSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        return Notification.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):  # type: ignore[no-untyped-def]
        notification = self.get_object()
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)


class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer

    def get_queryset(self):  # type: ignore[no-untyped-def]
        return Favorite.objects.filter(user=self.request.user).select_related("business")

    def perform_create(self, serializer):  # type: ignore[no-untyped-def]
        serializer.save(user=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):  # type: ignore[no-untyped-def]
        return [permissions.AllowAny()] if self.action in {"list", "retrieve"} else [permissions.IsAuthenticated()]

    def get_queryset(self):  # type: ignore[no-untyped-def]
        user = self.request.user
        public = Review.objects.filter(is_visible=True)
        if not user.is_authenticated:
            return public
        if user.is_superuser:
            return Review.objects.all()
        return (public | Review.objects.filter(business_id__in=member_business_ids(user)) | Review.objects.filter(customer__user=user)).distinct()

    def perform_create(self, serializer):  # type: ignore[no-untyped-def]
        appointment_id = self.request.data.get("appointment")
        appointment = Appointment.objects.select_related("customer", "business", "employee", "service").get(pk=appointment_id)
        if appointment.customer.user_id != self.request.user.id or appointment.status != Appointment.Status.COMPLETED:
            raise PermissionDenied("Only the customer of a completed appointment may review it.")
        serializer.save(customer=appointment.customer, business=appointment.business, employee=appointment.employee, service=appointment.service)

    def perform_update(self, serializer):  # type: ignore[no-untyped-def]
        review = self.get_object()
        is_member = self.request.user.is_superuser or self.request.user.business_memberships.filter(business=review.business, is_active=True).exists()
        if not is_member:
            raise PermissionDenied("Only business managers can reply to a review.")
        serializer.save(response=self.request.data.get("response", review.response), responded_at=timezone.now())

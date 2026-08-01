from __future__ import annotations

from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsBusinessMember, member_business_ids

from .models import Branch, BranchWorkHour, Business, BusinessMember
from .serializers import (
    BranchSerializer,
    BranchWorkHourSerializer,
    BusinessMemberSerializer,
    BusinessOnboardingSerializer,
    BusinessSerializer,
    PublicBusinessSerializer,
)


class BusinessViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessSerializer
    lookup_field = "slug"

    def get_queryset(self):  # type: ignore[no-untyped-def]
        # Public discovery must work even when the browser has an unrelated JWT.
        if self.action in {"list", "retrieve", "booking_catalog"}:
            queryset = Business.objects.filter(is_active=True).prefetch_related("employees")
            query = self.request.query_params.get("q", "").strip()
            if query:
                provider_query = Q()
                for term in query.split():
                    provider_query &= (
                        Q(employees__first_name__icontains=term)
                        | Q(employees__last_name__icontains=term)
                        | Q(employees__specialty__icontains=term)
                    )
                queryset = queryset.filter(
                    Q(name__icontains=query)
                    | Q(description__icontains=query)
                    | provider_query
                ).distinct()
            return queryset
        return Business.objects.filter(id__in=member_business_ids(self.request.user))

    def get_permissions(self):  # type: ignore[no-untyped-def]
        return [permissions.IsAuthenticated()] if self.action in {"create", "update", "partial_update", "destroy", "onboard"} else [permissions.AllowAny()]

    def get_serializer_class(self):  # type: ignore[no-untyped-def]
        if self.action in {"list", "retrieve", "booking_catalog"}:
            return PublicBusinessSerializer
        if self.action == "onboard":
            return BusinessOnboardingSerializer
        return BusinessSerializer

    @action(detail=False, methods=["post"], url_path="onboard")
    def onboard(self, request):  # type: ignore[no-untyped-def]
        serializer = BusinessOnboardingSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        business = serializer.save()
        return Response(PublicBusinessSerializer(business).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], permission_classes=[permissions.AllowAny])
    def booking_catalog(self, request, slug=None):  # type: ignore[no-untyped-def]
        """Public, tenant-safe data needed by the booking flow without exposing management APIs."""
        business = self.get_object()
        from catalog.models import Service
        from workforce.models import Employee

        branches = business.branches.filter(is_active=True).values("id", "name", "address", "timezone")
        services = Service.objects.filter(business=business, is_active=True).prefetch_related("branches").values("id", "name", "description", "price", "duration_minutes", "requires_deposit", "deposit_amount")
        employees = Employee.objects.filter(business=business, is_active=True).values("id", "first_name", "last_name", "specialty")
        return Response({"business": PublicBusinessSerializer(business).data, "branches": list(branches), "services": list(services), "employees": list(employees)})


class TenantFilteredViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsBusinessMember]
    business_lookup = "business_id"

    def get_queryset(self):  # type: ignore[no-untyped-def]
        queryset = super().get_queryset()
        return queryset.filter(**{f"{self.business_lookup}__in": member_business_ids(self.request.user)})

    def _business_from_validated_data(self, validated_data):  # type: ignore[no-untyped-def]
        current = validated_data.get("business")
        if current:
            return current
        parts = self.business_lookup.split("__")
        current = validated_data.get(parts[0])
        for part in parts[1:]:
            if current is None:
                return None
            attribute = part.removesuffix("_id")
            current = getattr(current, attribute, None)
        return current

    def _validate_write_tenant(self, serializer) -> None:  # type: ignore[no-untyped-def]
        business = self._business_from_validated_data(serializer.validated_data)
        if business is None and serializer.instance is not None:
            business = serializer.instance
            for part in self.business_lookup.split("__"):
                business = getattr(business, part.removesuffix("_id"), None)
                if business is None:
                    break
        business_id = getattr(business, "id", business)
        if not self.request.user.is_superuser and not self.request.user.business_memberships.filter(business_id=business_id, is_active=True).exists():
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You cannot write data for this business.")

    def perform_create(self, serializer):  # type: ignore[no-untyped-def]
        self._validate_write_tenant(serializer)
        serializer.save()

    def perform_update(self, serializer):  # type: ignore[no-untyped-def]
        self._validate_write_tenant(serializer)
        serializer.save()


class BranchViewSet(TenantFilteredViewSet):
    queryset = Branch.objects.select_related("business")
    serializer_class = BranchSerializer


class BranchWorkHourViewSet(TenantFilteredViewSet):
    queryset = BranchWorkHour.objects.select_related("branch", "branch__business")
    serializer_class = BranchWorkHourSerializer
    business_lookup = "branch__business_id"


class BusinessMemberViewSet(TenantFilteredViewSet):
    queryset = BusinessMember.objects.select_related("business", "user").prefetch_related("branches")
    serializer_class = BusinessMemberSerializer

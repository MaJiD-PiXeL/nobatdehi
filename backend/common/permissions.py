from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsBusinessMember(BasePermission):
    """Allows access only to a member of the object/query tenant."""

    message = "You do not have access to this business."

    def has_object_permission(self, request, view, obj) -> bool:  # type: ignore[no-untyped-def]
        if request.user.is_superuser:
            return True
        business_id = getattr(obj, "business_id", None) or getattr(obj, "id", None)
        return request.user.business_memberships.filter(business_id=business_id, is_active=True).exists()


def member_business_ids(user):  # type: ignore[no-untyped-def]
    if user.is_superuser:
        from tenants.models import Business

        return Business.objects.values_list("id", flat=True)
    return user.business_memberships.filter(is_active=True).values_list("business_id", flat=True)


from rest_framework import viewsets

from common.permissions import member_business_ids
from tenants.views import TenantFilteredViewSet

from .models import Service, ServiceCategory
from .serializers import ServiceCategorySerializer, ServiceSerializer


class ServiceCategoryViewSet(TenantFilteredViewSet):
    queryset = ServiceCategory.objects.select_related("business")
    serializer_class = ServiceCategorySerializer


class ServiceViewSet(TenantFilteredViewSet):
    queryset = Service.objects.select_related("business", "category").prefetch_related("branches")
    serializer_class = ServiceSerializer


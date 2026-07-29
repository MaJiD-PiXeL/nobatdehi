from rest_framework.routers import DefaultRouter

from .views import ServiceCategoryViewSet, ServiceViewSet

router = DefaultRouter()
router.register("service-categories", ServiceCategoryViewSet, basename="service-category")
router.register("services", ServiceViewSet, basename="service")

urlpatterns = router.urls


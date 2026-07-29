from rest_framework.routers import DefaultRouter

from .views import AppointmentDiscountViewSet, DiscountCodeViewSet, PaymentViewSet, RefundViewSet

router = DefaultRouter()
router.register("discount-codes", DiscountCodeViewSet, basename="discount-code")
router.register("payments", PaymentViewSet, basename="payment")
router.register("refunds", RefundViewSet, basename="refund")
router.register("discount", AppointmentDiscountViewSet, basename="discount")

urlpatterns = router.urls


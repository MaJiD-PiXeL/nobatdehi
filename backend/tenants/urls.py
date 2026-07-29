from rest_framework.routers import DefaultRouter

from .views import BranchViewSet, BranchWorkHourViewSet, BusinessMemberViewSet, BusinessViewSet

router = DefaultRouter()
router.register("businesses", BusinessViewSet, basename="business")
router.register("branches", BranchViewSet, basename="branch")
router.register("branch-work-hours", BranchWorkHourViewSet, basename="branch-work-hour")
router.register("business-members", BusinessMemberViewSet, basename="business-member")

urlpatterns = router.urls


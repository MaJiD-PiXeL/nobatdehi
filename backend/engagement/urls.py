from rest_framework.routers import DefaultRouter

from .views import FavoriteViewSet, NotificationViewSet, ReviewViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")
router.register("favorites", FavoriteViewSet, basename="favorite")
router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = router.urls


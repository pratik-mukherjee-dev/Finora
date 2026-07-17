from rest_framework.routers import DefaultRouter

from .views import LedgerViewSet

router = DefaultRouter()
router.register("", LedgerViewSet, basename="ledger")

urlpatterns = router.urls

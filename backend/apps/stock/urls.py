from rest_framework.routers import DefaultRouter
from .views import StockLedgerViewSet, StockConversionViewSet

router = DefaultRouter()
router.register("ledger", StockLedgerViewSet, basename="stockledger")
router.register("conversions", StockConversionViewSet, basename="stockconversion")
urlpatterns = router.urls

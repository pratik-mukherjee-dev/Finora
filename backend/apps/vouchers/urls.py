from rest_framework.routers import DefaultRouter
from .views import (
    SaleMasterViewSet, SaleDerivedViewSet, PurchaseViewSet,
    ReceivedViewSet, PaymentViewSet, VoucherNumberSeqViewSet,
)

router = DefaultRouter()
router.register("sales", SaleMasterViewSet, basename="sale")
router.register("sales-derived", SaleDerivedViewSet, basename="sale-derived")
router.register("purchases", PurchaseViewSet, basename="purchase")
router.register("received", ReceivedViewSet, basename="received")
router.register("payments", PaymentViewSet, basename="payment")
router.register("number-seqs", VoucherNumberSeqViewSet, basename="number-seq")
urlpatterns = router.urls

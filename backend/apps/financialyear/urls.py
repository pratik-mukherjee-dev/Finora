from rest_framework.routers import DefaultRouter
from .views import FinancialYearViewSet

router = DefaultRouter()
router.register("", FinancialYearViewSet, basename="financialyear")
urlpatterns = router.urls

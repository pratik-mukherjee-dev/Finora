from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, SettingViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("settings", SettingViewSet, basename="setting")
urlpatterns = router.urls

from rest_framework.routers import DefaultRouter
from .views import ItemViewSet, ItemCategoryViewSet, ItemCompanyMappingViewSet

router = DefaultRouter()
router.register("items", ItemViewSet, basename="item")
router.register("categories", ItemCategoryViewSet, basename="category")
router.register("mappings", ItemCompanyMappingViewSet, basename="mapping")
urlpatterns = router.urls

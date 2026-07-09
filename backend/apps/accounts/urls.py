from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .auth_views import LogoutView, MeView
from .views import CompanyViewSet, SettingViewSet


router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("settings", SettingViewSet, basename="setting")
urlpatterns = router.urls

urlpatterns += [
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
]
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Company
from .serializers import CompanySerializer, UserCompanySettingSerializer
from . import services, selectors


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        services.create_company(
            self.request.user,
            serializer.validated_data["name"],
            serializer.validated_data.get("is_default", False),
        )


class SettingViewSet(viewsets.ViewSet):
    def list(self, request):
        s = selectors.user_setting(request.user)
        return Response(UserCompanySettingSerializer(s).data if s else {})

    @action(detail=False, methods=["post"])
    def switch_multi(self, request):
        s = services.switch_to_multi(
            request.user, request.data.get("segregation_enabled", False)
        )
        return Response(UserCompanySettingSerializer(s).data)

    @action(detail=False, methods=["post"])
    def segregation(self, request):
        s = services.set_segregation(request.user, bool(request.data.get("enabled")))
        return Response(UserCompanySettingSerializer(s).data)

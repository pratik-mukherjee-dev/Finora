from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Company,
    SettlementMode,
    CompanyBankDetail,
)
from .serializers import (
    CompanySerializer,
    UserCompanySettingSerializer,
    SettlementModeSerializer,
    LicenseSerializer,
    CompanyBankDetailSerializer,
)
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

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        is_active = request.data.get("is_active", True)
        company = services.set_company_active(request.user, pk, bool(is_active))
        return Response(CompanySerializer(company).data)

    @action(detail=True, methods=["post"])
    def make_default(self, request, pk=None):
        company = services.set_default_company(request.user, pk)
        return Response(CompanySerializer(company).data)


class SettingViewSet(viewsets.ViewSet):
    def list(self, request):
        setting = selectors.user_setting(request.user)
        lic = selectors.user_license(request.user)
        data = UserCompanySettingSerializer(setting).data if setting else None
        data["license"] = LicenseSerializer(lic).data if lic else None
        return Response(data)

    @action(detail=False, methods=["post"])
    def switch_multi(self, request):
        s = services.switch_to_multi(
            request.user, request.data.get("segregation_enabled", False)
        )
        return Response(UserCompanySettingSerializer(s).data)

    @action(detail=False, methods=["post"])
    def switch_single(self, request):
        s = services.switch_to_single(request.user)
        return Response(UserCompanySettingSerializer(s).data)

    @action(detail=False, methods=["post"])
    def segregation(self, request):
        s = services.set_segregation(request.user, bool(request.data.get("enabled")))
        return Response(UserCompanySettingSerializer(s).data)

    @action(detail=False, methods=["post"])
    def upgrade_multi(self, request):
        max_companies = int(request.data.get("max_companies", 5))
        lic = services.upgrade_to_multi_license(request.user, max_companies)
        return Response(LicenseSerializer(lic).data)

    @action(detail=False, methods=["post"])
    def downgrade_single(self, request):
        lic = services.downgrade_to_single_license(request.user)
        return Response(LicenseSerializer(lic).data)


class SettlementModeViewSet(viewsets.ModelViewSet):
    serializer_class = SettlementModeSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        return SettlementMode.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_system=False, created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        services.delete_settlement_mode(request.user, kwargs["pk"])
        from rest_framework.response import Response
        return Response(status=204)


class CompanyBankDetailViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyBankDetailSerializer
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        qs = CompanyBankDetail.objects.filter(company__user=self.request.user)
        company_id = self.request.query_params.get("company")
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs

    def perform_create(self, serializer):
        company = Company.objects.get(
            user=self.request.user, pk=serializer.validated_data["company"].id
        )
        # If marking as default, unset any existing default
        if serializer.validated_data.get("is_default"):
            CompanyBankDetail.objects.filter(
                company=company, is_default=True
            ).update(is_default=False)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.validated_data.get("is_default"):
            CompanyBankDetail.objects.filter(
                company=serializer.instance.company, is_default=True
            ).exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()

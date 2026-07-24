from rest_framework import serializers
from .models import Company, UserCompanySetting, License, SettlementMode, CompanyBankDetail


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "is_default", "is_active", "created_at"]
        read_only_fields = ["created_at"]


class UserCompanySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCompanySetting
        fields = ["active_mode", "default_company", "segregation_enabled", "is_mode_locked"]
        read_only_fields = ["active_mode", "is_mode_locked"]


class LicenseSerializer(serializers.ModelSerializer):
    allows_multi = serializers.BooleanField(read_only=True)

    class Meta:
        model = License
        fields = ["plan", "mode", "is_active", "valid_till", "allows_multi", "max_companies"]


class SettlementModeSerializer(serializers.ModelSerializer):
    needs_reference = serializers.BooleanField(read_only=True)

    class Meta:
        model = SettlementMode
        fields = [
            'id', 'name', 'category', 'bank_type',
            'is_system', 'is_active',
            'sort_order', 'needs_reference',
        ]
        read_only_fields = ['is_system', 'needs_reference']


class CompanyBankDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyBankDetail
        fields = [
            "id", "company", "bank_name", "account_number", "ifsc_code",
            "branch", "account_holder", "upi_id", "is_default",
        ]
        read_only_fields = ["id"]

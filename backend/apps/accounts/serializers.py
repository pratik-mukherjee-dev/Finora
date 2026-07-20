from rest_framework import serializers
from .models import Company, UserCompanySetting, License, SettlementMode


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "is_default", "created_at"]
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
    class Meta:
        model = SettlementMode
        fields = ['id', 'name', 'is_system', 'is_active', 'sort_order']
        read_only_fields = ['is_system']


from rest_framework import serializers
from .models import FinancialYear


class FinancialYearSerializer(serializers.ModelSerializer):
    is_writable = serializers.BooleanField(read_only=True)

    class Meta:
        model = FinancialYear
        fields = ["id", "start_date", "end_date", "is_active", "is_closed", "is_writable"]
        read_only_fields = ["is_active", "is_closed"]

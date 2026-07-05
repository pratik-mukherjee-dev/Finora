from rest_framework import serializers
from .models import StockLedger, StockConversion


class StockLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLedger
        fields = [
            "id", "mapping", "date", "qty_in", "qty_out", "balance",
            "voucher_type", "voucher_id", "is_manual", "is_reversal", "is_opening",
        ]


class StockConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockConversion
        fields = [
            "id", "date", "source_mapping", "target_mapping",
            "source_qty", "target_qty", "is_cancelled",
        ]
        read_only_fields = ["is_cancelled"]

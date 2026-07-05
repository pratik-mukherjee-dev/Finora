from rest_framework import serializers
from .models import Party, PartyLedger


class PartySerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Party
        fields = ["id", "name", "phone", "address", "opening_balance", "balance", "created_at"]
        read_only_fields = ["created_at"]

    def get_balance(self, obj):
        from .selectors import current_balance
        return current_balance(obj)


class PartyLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartyLedger
        fields = [
            "id", "date", "voucher_type", "voucher_id",
            "debit", "credit", "balance", "is_reversal",
        ]

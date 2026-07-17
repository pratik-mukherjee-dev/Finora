from rest_framework import serializers

from .models import (
    SaleMaster, SaleDerived, SaleLine, Purchase, PurchaseLine,
    Received, Payment, Allocation, VoucherNumberSeq, VoucherCharge,
)


class VoucherChargeSerializer(serializers.ModelSerializer):
    ledger_name = serializers.CharField(source="ledger.name", read_only=True)

    class Meta:
        model = VoucherCharge
        fields = [
            "id", "ledger", "ledger_name", "charge_type", "mode",
            "input_value", "amount", "sort_order",
        ]
        read_only_fields = ["amount", "sort_order"]



class SaleLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    company_name = serializers.CharField(source="company_resolved.name", read_only=True)

    class Meta:
        model = SaleLine
        fields = [
            "id", "item", "item_name", "mapping", "company_resolved",
            "company_name", "derived", "qty", "rate", "amount",
        ]
        read_only_fields = fields


class SaleDerivedSerializer(serializers.ModelSerializer):
    lines = SaleLineSerializer(many=True, read_only=True)
    charges = serializers.SerializerMethodField()

    class Meta:
        model = SaleDerived
        fields = [
            "id", "company", "number", "date", "total_amount",
            "master", "is_cancelled", "lines", "charges",
        ]
        read_only_fields = fields

    def get_charges(self, obj):
        from .models import VoucherCharge
        qs = VoucherCharge.objects.filter(voucher_type="SALE_DERIVED", voucher_id=obj.id)
        return VoucherChargeSerializer(qs, many=True).data



class SaleMasterSerializer(serializers.ModelSerializer):
    lines = SaleLineSerializer(many=True, read_only=True)
    derived = SaleDerivedSerializer(many=True, read_only=True)
    charges = serializers.SerializerMethodField()

    class Meta:
        model = SaleMaster
        fields = [
            "id", "company", "party", "number", "date", "segregate",
            "total_amount", "is_cancelled", "lines", "derived", "charges",
        ]
        read_only_fields = ["number", "total_amount", "is_cancelled",
                            "lines", "derived", "charges"]

    def get_charges(self, obj):
        from .models import VoucherCharge
        qs = VoucherCharge.objects.filter(voucher_type="SALE", voucher_id=obj.id, is_cancelled=False)
        return VoucherChargeSerializer(qs, many=True).data



class PurchaseLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = PurchaseLine
        fields = ["id", "item", "item_name", "mapping", "qty", "rate", "amount"]
        read_only_fields = ["item", "amount"]


class PurchaseSerializer(serializers.ModelSerializer):
    lines = PurchaseLineSerializer(many=True, read_only=True)
    party_name = serializers.CharField(source="party.name", read_only=True)
    charges = serializers.SerializerMethodField()

    class Meta:
        model = Purchase
        fields = [
            "id", "company", "party", "party_name", "number", "date",
            "total_amount", "is_cancelled", "lines", "charges",
        ]
        read_only_fields = ["number", "total_amount", "is_cancelled",
                            "lines", "charges"]

    def get_charges(self, obj):
        from .models import VoucherCharge
        qs = VoucherCharge.objects.filter(voucher_type="PURCHASE", voucher_id=obj.id, is_cancelled=False)
        return VoucherChargeSerializer(qs, many=True).data


class ReceivedSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.name", read_only=True)

    class Meta:
        model = Received
        fields = ["id", "company", "party", "party_name", "number", "date", "amount", "is_cancelled"]
        read_only_fields = ["number", "is_cancelled"]


class PaymentSerializer(serializers.ModelSerializer):
    party_name = serializers.CharField(source="party.name", read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "company", "party", "party_name", "number", "date", "amount", "is_cancelled"]
        read_only_fields = ["number", "is_cancelled"]


class AllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allocation
        fields = [
            "id", "settlement_type", "settlement_id",
            "bill_type", "bill_id", "amount", "is_reversal",
        ]


class VoucherNumberSeqSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoucherNumberSeq
        fields = ["id", "company", "financial_year", "voucher_type", "template", "high_water"]
        read_only_fields = ["high_water"]

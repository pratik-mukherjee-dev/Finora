from rest_framework import serializers
from .models import Ledger


class LedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ledger
        fields = ["id", "company", "name", "kind", "is_system", "gst_rate"]
        read_only_fields = ["is_system"]


from rest_framework import serializers
from .models import Item, ItemCategory, ItemCompanyMapping


class ItemCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCategory
        fields = ["id", "company", "name"]


class ItemCompanyMappingSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = ItemCompanyMapping
        fields = [
            "id", "item", "item_name", "company", "company_name", "category",
            "rate", "stock", "opening_stock", "hsn_code", "gst_rate", "gst_mode",
        ]
        read_only_fields = ["stock"]


class ItemSerializer(serializers.ModelSerializer):
    mappings = ItemCompanyMappingSerializer(many=True, read_only=True)

    class Meta:
        model = Item
        fields = ["id", "name", "base_unit", "created_at", "mappings"]
        read_only_fields = ["created_at"]

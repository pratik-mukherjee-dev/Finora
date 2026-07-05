from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import Company
from .models import Item, ItemCategory, ItemCompanyMapping
from .serializers import (
    ItemSerializer, ItemCategorySerializer, ItemCompanyMappingSerializer,
)
from .filters import MappingFilter, CategoryFilter
from . import services


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer

    def get_queryset(self):
        return Item.objects.filter(user=self.request.user).prefetch_related(
            "mappings__company", "mappings__category"
        )

    def perform_create(self, serializer):
        company_id = self.request.data.get("company")
        company = Company.objects.filter(user=self.request.user, pk=company_id).first()
        services.create_item(
            self.request.user, serializer.validated_data["name"],
            company=company,
            base_unit=serializer.validated_data.get("base_unit", "pcs"),
        )

    @action(detail=True, methods=["post"])
    def add_mapping(self, request, pk=None):
        item = self.get_object()
        company = Company.objects.get(user=request.user, pk=request.data["company"])
        category = None
        if request.data.get("category"):
            category = ItemCategory.objects.get(
                company=company, pk=request.data["category"]
            )
        m = services.add_mapping(
            item, company, rate=request.data.get("rate", 0), category=category,
            opening_stock=request.data.get("opening_stock", 0),
        )
        return Response(ItemCompanyMappingSerializer(m).data, status=201)


class ItemCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ItemCategorySerializer
    filterset_class = CategoryFilter

    def get_queryset(self):
        return ItemCategory.objects.filter(company__user=self.request.user)


class ItemCompanyMappingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ItemCompanyMappingSerializer
    filterset_class = MappingFilter

    def get_queryset(self):
        return ItemCompanyMapping.objects.filter(
            company__user=self.request.user
        ).select_related("item", "company", "category")

from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.exceptions import FinancialYearLocked
from apps.financialyear.selectors import active_fy
from apps.catalogue.models import ItemCompanyMapping, Item
from .models import StockLedger, StockConversion
from .serializers import StockLedgerSerializer, StockConversionSerializer
from .filters import StockLedgerFilter
from . import services


class StockLedgerViewSet(
    mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = StockLedgerSerializer
    filterset_class = StockLedgerFilter

    def get_queryset(self):
        return StockLedger.objects.filter(mapping__company__user=self.request.user)

    @action(detail=False, methods=["post"])
    def adjust(self, request):
        fy = active_fy(request.user)
        if not fy:
            raise FinancialYearLocked()
        mapping = ItemCompanyMapping.objects.get(
            pk=request.data["mapping"], company__user=request.user
        )
        entry = services.manual_adjust(
            mapping.id, request.data["date"], fy, request.data["new_stock"]
        )
        return Response(StockLedgerSerializer(entry).data if entry else {}, status=201)


class StockConversionViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = StockConversionSerializer

    def get_queryset(self):
        return StockConversion.objects.filter(user=self.request.user)

    def create(self, request):
        fy = active_fy(request.user)
        if not fy:
            raise FinancialYearLocked()
        source = ItemCompanyMapping.objects.get(
            pk=request.data["source_mapping"], company__user=request.user
        )
        target_item = Item.objects.get(pk=request.data["target_item"], user=request.user)
        conv = services.convert(
            request.user, request.data["date"], fy, source,
            request.data["source_qty"], target_item, request.data["target_qty"],
        )
        return Response(StockConversionSerializer(conv).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        fy = active_fy(request.user)
        if not fy:
            raise FinancialYearLocked()
        conv = services.cancel_conversion(pk, request.data.get("date", fy.start_date), fy)
        return Response(StockConversionSerializer(conv).data)

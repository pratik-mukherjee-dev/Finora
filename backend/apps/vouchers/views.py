from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.exceptions import FinancialYearLocked, DomainError
from apps.financialyear.selectors import active_fy
from apps.accounts.models import Company
from apps.parties.models import Party
from .models import SaleMaster, SaleDerived, Purchase, Received, Payment, VoucherNumberSeq
from .serializers import (
    SaleMasterSerializer, SaleDerivedSerializer, PurchaseSerializer,
    ReceivedSerializer, PaymentSerializer, VoucherNumberSeqSerializer,
)
from . import services


def _context(request):
    fy = active_fy(request.user)
    if not fy:
        raise FinancialYearLocked("No active financial year.")
    company = Company.objects.get(user=request.user, pk=request.data["company"])
    party = Party.objects.get(user=request.user, pk=request.data["party"])
    return fy, company, party


class SaleMasterViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = SaleMasterSerializer

    def get_queryset(self):
        return SaleMaster.objects.filter(company__user=self.request.user).prefetch_related(
            "lines", "derived__lines"
        )

    def create(self, request):
        fy, company, party = _context(request)
        master = services.create_sale(
            request.user, company, fy, party, request.data["date"],
            request.data["lines"], number=request.data.get("number"),
            segregate_flag=request.data.get("segregate"),
        )
        return Response(self.get_serializer(master).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        master = services.cancel_sale(request.user, pk)
        return Response(self.get_serializer(master).data)


class SaleDerivedViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = SaleDerivedSerializer

    def get_queryset(self):
        qs = SaleDerived.objects.filter(company__user=self.request.user).prefetch_related("lines")
        master_id = self.request.query_params.get("master")
        return qs.filter(master_id=master_id) if master_id else qs


class PurchaseViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = PurchaseSerializer

    def get_queryset(self):
        return Purchase.objects.filter(company__user=self.request.user).prefetch_related("lines")

    def create(self, request):
        fy, company, party = _context(request)
        p = services.create_purchase(
            request.user, company, fy, party, request.data["date"],
            request.data["lines"], number=request.data.get("number"),
        )
        return Response(self.get_serializer(p).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        p = services.cancel_purchase(request.user, pk)
        return Response(self.get_serializer(p).data)


class ReceivedViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = ReceivedSerializer

    def get_queryset(self):
        return Received.objects.filter(company__user=self.request.user)

    def create(self, request):
        fy, company, party = _context(request)
        r = services.create_received(
            request.user, company, fy, party, request.data["date"],
            request.data["amount"], number=request.data.get("number"),
        )
        return Response(self.get_serializer(r).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        r = services.cancel_received(request.user, pk)
        return Response(self.get_serializer(r).data)


class PaymentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(company__user=self.request.user)

    def create(self, request):
        fy, company, party = _context(request)
        p = services.create_payment(
            request.user, company, fy, party, request.data["date"],
            request.data["amount"], number=request.data.get("number"),
        )
        return Response(self.get_serializer(p).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        p = services.cancel_payment(request.user, pk)
        return Response(self.get_serializer(p).data)


class VoucherNumberSeqViewSet(viewsets.ModelViewSet):
    serializer_class = VoucherNumberSeqSerializer
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        return VoucherNumberSeq.objects.filter(company__user=self.request.user)

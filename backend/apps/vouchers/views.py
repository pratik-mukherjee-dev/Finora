from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.exceptions import FinancialYearLocked, DomainError
from apps.financialyear.selectors import active_fy
from apps.accounts.models import Company
from apps.parties.models import Party
from .models import (
    SaleMaster, SaleDerived, Purchase, Received, Payment,
    Allocation, VoucherNumberSeq,
)
from .serializers import (
    SaleMasterSerializer, SaleDerivedSerializer, PurchaseSerializer,
    ReceivedSerializer, PaymentSerializer, VoucherNumberSeqSerializer,
)
from .selectors import open_bills_preview
from . import services


def _context(request):
    fy = active_fy(request.user)
    if not fy:
        raise FinancialYearLocked("No active financial year.")
    company = Company.objects.get(user=request.user, pk=request.data["company"])
    party = Party.objects.get(user=request.user, pk=request.data["party"])
    return fy, company, party


def _allocation_rows(settlement_type, settlement_id):
    """Allocations for a settlement, enriched with each bill's number/date."""
    allocs = Allocation.objects.filter(
        settlement_type=settlement_type,
        settlement_id=settlement_id,
        is_reversal=False,
    ).order_by("id")

    bill_model = {"SALE": SaleMaster, "PURCHASE": Purchase}
    rows = []
    for a in allocs:
        model = bill_model.get(a.bill_type)
        bill = model.objects.filter(pk=a.bill_id).first() if model else None
        rows.append({
            "id": a.id,
            "bill_type": a.bill_type,
            "bill_id": a.bill_id,
            "bill_number": bill.number if bill else None,
            "bill_date": bill.date if bill else None,
            "bill_total": bill.total_amount if bill else None,
            "amount": a.amount,
        })
    return rows


def _apply_history_filters(qs, request):
    """Optional ?company= and ?party= narrowing for history lists."""
    company_id = request.query_params.get("company")
    party_id = request.query_params.get("party")
    if company_id:
        qs = qs.filter(company_id=company_id)
    if party_id:
        qs = qs.filter(party_id=party_id)
    return qs


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
        qs = Purchase.objects.filter(
            company__user=self.request.user
        ).select_related("party").prefetch_related("lines")
        return _apply_history_filters(qs, self.request)

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
        qs = Received.objects.filter(
            company__user=self.request.user
        ).select_related("party")
        return _apply_history_filters(qs, self.request)

    def create(self, request):
        fy, company, party = _context(request)
        r = services.create_received(
            request.user, company, fy, party, request.data["date"],
            request.data["amount"], number=request.data.get("number"),
        )
        data = self.get_serializer(r).data
        data["allocations"] = _allocation_rows("RECEIVED", r.id)
        return Response(data, status=201)

    @action(detail=True, methods=["get"])
    def allocations(self, request, pk=None):
        r = self.get_object()
        return Response(_allocation_rows("RECEIVED", r.id))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        r = services.cancel_received(request.user, pk)
        return Response(self.get_serializer(r).data)

    @action(detail=False, methods=["get"])
    def open_bills(self, request):
        """Live preview of open sales this receipt would settle (oldest->latest)."""
        party = Party.objects.get(user=request.user, pk=request.query_params["party"])
        return Response(open_bills_preview(party, "RECEIVED"))



class PaymentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = PaymentSerializer

    def get_queryset(self):
        qs = Payment.objects.filter(
            company__user=self.request.user
        ).select_related("party")
        return _apply_history_filters(qs, self.request)

    def create(self, request):
        fy, company, party = _context(request)
        p = services.create_payment(
            request.user, company, fy, party, request.data["date"],
            request.data["amount"], number=request.data.get("number"),
        )
        data = self.get_serializer(p).data
        data["allocations"] = _allocation_rows("PAYMENT", p.id)
        return Response(data, status=201)

    @action(detail=True, methods=["get"])
    def allocations(self, request, pk=None):
        p = self.get_object()
        return Response(_allocation_rows("PAYMENT", p.id))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        p = services.cancel_payment(request.user, pk)
        return Response(self.get_serializer(p).data)

    @action(detail=False, methods=["get"])
    def open_bills(self, request):
        """Live preview of open purchases this payment would settle (oldest->latest)."""
        party = Party.objects.get(user=request.user, pk=request.query_params["party"])
        return Response(open_bills_preview(party, "PAYMENT"))


class VoucherNumberSeqViewSet(viewsets.ModelViewSet):
    serializer_class = VoucherNumberSeqSerializer
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        return VoucherNumberSeq.objects.filter(company__user=self.request.user)

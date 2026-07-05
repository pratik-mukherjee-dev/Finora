from decimal import Decimal
from django.db.models import Sum

from ..models import SaleMaster, Purchase, Allocation


def _allocated(bill_type, bill_id):
    agg = Allocation.objects.filter(
        bill_type=bill_type, bill_id=bill_id, is_reversal=False
    ).aggregate(s=Sum("amount"))
    return agg["s"] or Decimal("0.00")


def open_sales(party):
    bills = SaleMaster.objects.filter(party=party).order_by("date", "id")
    out = []
    for b in bills:
        pending = b.total_amount - _allocated("SALE", b.id)
        if pending > 0:
            out.append((b, pending))
    return out


def open_purchases(party):
    bills = Purchase.objects.filter(party=party).order_by("date", "id")
    out = []
    for b in bills:
        pending = b.total_amount - _allocated("PURCHASE", b.id)
        if pending > 0:
            out.append((b, pending))
    return out

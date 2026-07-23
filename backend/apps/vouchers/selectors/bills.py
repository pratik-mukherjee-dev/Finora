from decimal import Decimal
from django.db.models import Sum

from ..models import SaleMaster, Purchase, Allocation, Received, Payment


def _allocated(bill_type, bill_id):
    agg = Allocation.objects.filter(
        bill_type=bill_type, bill_id=bill_id, is_reversal=False
    ).aggregate(s=Sum("amount"))
    return agg["s"] or Decimal("0.00")


def _open_bills(bill_model, bill_type, party):
    """
    Shared core: outstanding bills for a party, oldest -> latest.
    Returns a list of (bill, pending) tuples. Cancelled bills excluded.
    """
    bills = bill_model.objects.filter(
        party=party, is_cancelled=False
    ).order_by("date", "id")
    out = []
    for b in bills:
        pending = b.total_amount - _allocated(bill_type, b.id)
        if pending > 0:
            out.append((b, pending))
    return out


def open_sales(party):
    return _open_bills(SaleMaster, "SALE", party)


def open_purchases(party):
    return _open_bills(Purchase, "PURCHASE", party)


def _total_settled(settlement_model, settlement_type, party):
    """Sum of all non-cancelled settlement voucher amounts for this party."""
    agg = settlement_model.objects.filter(
        party=party, is_cancelled=False
    ).aggregate(s=Sum("amount"))
    return agg["s"] or Decimal("0.00")


def _total_allocated_for_party(settlement_model, settlement_type, party):
    """Sum of all non-reversal allocation amounts for settlements belonging
    to this party."""
    settlement_ids = settlement_model.objects.filter(
        party=party, is_cancelled=False
    ).values_list("id", flat=True)
    agg = Allocation.objects.filter(
        settlement_type=settlement_type,
        settlement_id__in=settlement_ids,
        is_reversal=False,
    ).aggregate(s=Sum("amount"))
    return agg["s"] or Decimal("0.00")


def open_bills_preview(party, kind):
    """
    Read-only dry-run for the settlement UI. `kind` is the settlement kind:
      RECEIVED -> settles open SALES
      PAYMENT  -> settles open PURCHASES

    Returns:
      outstanding_total: sum of unpaid bill amounts
      balance:           party ledger balance (positive = receivable)
      on_account:        settlement money received/paid but NOT allocated to
                         any bill (i.e. advance / overpayment for this side)
      bills:             list of open bills with per-bill detail

    on_account is computed as:
      total settlement voucher amounts - total allocation amounts
    This gives the actual unallocated money, not a derived residual.
    """
    from apps.parties.selectors import current_balance

    if kind == "RECEIVED":
        bill_type, pairs = "SALE", open_sales(party)
        settle_model = Received
    elif kind == "PAYMENT":
        bill_type, pairs = "PURCHASE", open_purchases(party)
        settle_model = Payment
    else:
        return {
            "outstanding_total": Decimal("0.00"),
            "balance": Decimal("0.00"),
            "on_account": Decimal("0.00"),
            "bills": []
        }

    rows = []
    total = Decimal("0.00")
    for bill, pending in pairs:
        settled = bill.total_amount - pending
        total += pending
        rows.append({
            "bill_type": bill_type,
            "bill_id": bill.id,
            "number": bill.number,
            "date": bill.date,
            "total": bill.total_amount,
            "settled": settled,
            "open": pending,
        })

    bal = current_balance(party)

    # on_account = total money settled - total money allocated to bills
    # This is the actual unallocated advance/overpayment for this stream.
    total_settled = _total_settled(settle_model, kind, party)
    total_alloc = _total_allocated_for_party(settle_model, kind, party)
    on_account = max(total_settled - total_alloc, Decimal("0.00"))

    return {
        "outstanding_total": total,
        "balance": bal,
        "on_account": on_account,
        "bills": rows
    }

from decimal import Decimal
from django.db.models import Sum

from ..models import SaleMaster, Purchase, Allocation


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


def open_bills_preview(party, kind):
    """
        Read-only dry-run for the settlement UI. `kind` is the settlement kind:
          RECEIVED -> settles open SALES
          PAYMENT  -> settles open PURCHASES
        Returns rich rows + outstanding total + ledger balance + on_account.

        Accounting identity:
          RECEIVED:  balance = outstanding - on_account   (positive = receivable)
          PAYMENT:  -balance = outstanding - on_account   (negative = payable)
    """
    from apps.parties.selectors import current_balance

    if kind == "RECEIVED":
        bill_type, pairs = "SALE", open_sales(party)
    elif kind == "PAYMENT":
        bill_type, pairs = "PURCHASE", open_purchases(party)
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
    # on_account = how much receipt/payment money is sitting unallocated.
    # For RECEIVED: bal is positive (receivable). on_account = outstanding - bal
    # For PAYMENT:  bal is negative (payable).   on_account = outstanding - abs(bal)
    if kind == "RECEIVED":
        on_account = max(total - bal, Decimal("0.00"))
    else:
        on_account = max(total - abs(bal), Decimal("0.00"))

    return {
        "outstanding_total": total,
        "balance": bal,
        "on_account": on_account,
        "bills": rows
    }

from django.db import transaction
from django.db.models import Sum
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from apps.common.exceptions import DomainError
from ..models import Allocation, SaleMaster, Purchase
from ..selectors import open_sales, open_purchases


@transaction.atomic
def apply_receipt(received):
    _allocate(received.party, received.amount, "RECEIVED", received.id,
              "SALE", open_sales)


@transaction.atomic
def apply_payment(payment):
    _allocate(payment.party, payment.amount, "PAYMENT", payment.id,
              "PURCHASE", open_purchases)


@transaction.atomic
def apply_receipt_to_bill(received, bill_id):
    """Settle ONLY the given sale (used by inline sale settlement)."""
    _allocate_to_bill(received.party, received.amount, "RECEIVED", received.id,
                      "SALE", SaleMaster, bill_id)


@transaction.atomic
def apply_payment_to_bill(payment, bill_id):
    """Settle ONLY the given purchase (used by inline purchase settlement)."""
    _allocate_to_bill(payment.party, payment.amount, "PAYMENT", payment.id,
                      "PURCHASE", Purchase, bill_id)


def _allocate(party, amount, settlement_type, settlement_id, bill_type, open_fn):
    remaining = Decimal(str(amount))
    for bill, pending in open_fn(party):
        if remaining <= 0:
            break
        take = min(remaining, pending)
        Allocation.objects.create(
            settlement_type=settlement_type, settlement_id=settlement_id,
            bill_type=bill_type, bill_id=bill.id, amount=take,
        )
        remaining -= take


def _bill_pending(bill_type, bill_id, bill_total):
    agg = Allocation.objects.filter(
        bill_type=bill_type, bill_id=bill_id, is_reversal=False
    ).aggregate(s=Sum("amount"))
    return bill_total - (agg["s"] or Decimal("0.00"))


def _allocate_to_bill(party, amount, settlement_type, settlement_id,
                      bill_type, bill_model, bill_id):
    """Allocate against ONE specific bill only. Any excess over that bill's
    pending stays unallocated (on account) rather than spilling onto other
    open bills — that spill-over is what the Settle page is for."""
    try:
        bill = bill_model.objects.filter(
            pk=bill_id, party=party, is_cancelled=False
        ).first()
    except (ValueError, ValidationError):
        raise DomainError("Invalid target bill id.")

    if bill is None:
        raise DomainError("Target bill not found for this party.")

    pending = _bill_pending(bill_type, bill.id, bill.total_amount)
    take = min(Decimal(str(amount)), pending)
    if take > 0:
        Allocation.objects.create(
            settlement_type=settlement_type, settlement_id=settlement_id,
            bill_type=bill_type, bill_id=bill.id, amount=take,
        )


@transaction.atomic
def reverse_allocations(settlement_type, settlement_id):
    allocs = Allocation.objects.filter(
        settlement_type=settlement_type, settlement_id=settlement_id, is_reversal=False
    )
    for a in allocs:
        Allocation.objects.create(
            settlement_type=settlement_type, settlement_id=settlement_id,
            bill_type=a.bill_type, bill_id=a.bill_id,
            amount=-a.amount, is_reversal=True,
        )
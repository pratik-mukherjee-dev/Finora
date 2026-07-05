from django.db import transaction
from decimal import Decimal

from ..models import Allocation
from ..selectors import open_sales, open_purchases


@transaction.atomic
def apply_receipt(received):
    _allocate(received.party, received.amount, "RECEIVED", received.id,
              "SALE", open_sales)


@transaction.atomic
def apply_payment(payment):
    _allocate(payment.party, payment.amount, "PAYMENT", payment.id,
              "PURCHASE", open_purchases)


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

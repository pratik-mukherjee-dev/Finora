from django.db import transaction
from decimal import Decimal

from apps.common.exceptions import DomainError
from apps.parties.services import post_entry
from ..models import Received, Payment
from .numbering import next_number
from .reconciliation import (
    apply_receipt, apply_payment,
    apply_receipt_to_bill, apply_payment_to_bill,
)


@transaction.atomic
def create_received(
        user, company, fy, party, date, amount,
        number=None, mode=None, target_bill_id=None, transaction_ref=None):
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    amount = Decimal(str(amount))
    num = next_number(company, fy, "RECEIVED", manual=number)
    r = Received.objects.create(
        company=company, financial_year=fy, party=party, date=date,
        number=num, amount=amount, total_amount=amount, mode=mode,
        transaction_ref=transaction_ref or None, created_by=user,
    )
    post_entry(party, date, fy, "RECEIVED", r.id, credit=amount)
    if target_bill_id is not None:
        apply_receipt_to_bill(r, target_bill_id)
    else:
        apply_receipt(r)
    return r


@transaction.atomic
def create_payment(
        user, company, fy, party, date, amount,
        number=None, mode=None, target_bill_id=None, transaction_ref=None):
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    amount = Decimal(str(amount))
    num = next_number(company, fy, "PAYMENT", manual=number)
    p = Payment.objects.create(
        company=company, financial_year=fy, party=party, date=date,
        number=num, amount=amount, total_amount=amount, mode=mode,
        transaction_ref=transaction_ref or None, created_by=user,
    )
    post_entry(party, date, fy, "PAYMENT", p.id, debit=amount)
    if target_bill_id is not None:
        apply_payment_to_bill(p, target_bill_id)
    else:
        apply_payment(p)
    return p
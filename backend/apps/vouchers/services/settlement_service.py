from django.db import transaction
from decimal import Decimal

from apps.common.exceptions import DomainError
from apps.parties.services import post_entry
from ..models import Received, Payment
from .numbering import next_number
from .reconciliation import apply_receipt, apply_payment


@transaction.atomic
def create_received(user, company, fy, party, date, amount, number=None):
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    amount = Decimal(str(amount))
    num = next_number(company, fy, "RECEIVED", manual=number)
    r = Received.objects.create(
        company=company, financial_year=fy, party=party, date=date,
        number=num, amount=amount, total_amount=amount, created_by=user,
    )
    post_entry(party, date, fy, "RECEIVED", r.id, debit=amount)
    apply_receipt(r)
    return r


@transaction.atomic
def create_payment(user, company, fy, party, date, amount, number=None):
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    amount = Decimal(str(amount))
    num = next_number(company, fy, "PAYMENT", manual=number)
    p = Payment.objects.create(
        company=company, financial_year=fy, party=party, date=date,
        number=num, amount=amount, total_amount=amount, created_by=user,
    )
    post_entry(party, date, fy, "PAYMENT", p.id, credit=amount)
    apply_payment(p)
    return p

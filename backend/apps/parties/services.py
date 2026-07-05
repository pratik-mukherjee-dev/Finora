from django.db import transaction
from decimal import Decimal

from .models import Party, PartyLedger
from .selectors import current_balance


@transaction.atomic
def create_party(user, name, phone=None, address=None, opening_balance=Decimal("0.00")):
    return Party.objects.create(
        user=user, name=name.strip(), phone=phone, address=address,
        opening_balance=opening_balance,
    )


@transaction.atomic
def post_entry(party, date, fy, voucher_type, voucher_id,
               debit=Decimal("0.00"), credit=Decimal("0.00"), is_reversal=False):
    party = Party.objects.select_for_update().get(pk=party.pk)
    running = current_balance(party) + debit - credit
    return PartyLedger.objects.create(
        party=party, date=date, financial_year=fy,
        voucher_type=voucher_type, voucher_id=voucher_id,
        debit=debit, credit=credit, balance=running, is_reversal=is_reversal,
    )


@transaction.atomic
def reverse_entries(voucher_type, voucher_id, date, fy):
    entries = PartyLedger.objects.select_for_update().filter(
        voucher_type=voucher_type, voucher_id=voucher_id, is_reversal=False
    )
    for e in entries:
        post_entry(
            e.party, date, fy, voucher_type, voucher_id,
            debit=e.credit, credit=e.debit, is_reversal=True,
        )

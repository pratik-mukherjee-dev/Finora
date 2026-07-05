from decimal import Decimal
from django.db.models import Sum
from .models import Party, PartyLedger


def current_balance(party):
    agg = PartyLedger.objects.filter(party=party).aggregate(
        d=Sum("debit"), c=Sum("credit")
    )
    debit = agg["d"] or Decimal("0.00")
    credit = agg["c"] or Decimal("0.00")
    return party.opening_balance + debit - credit


def ledger_entries(party):
    return PartyLedger.objects.filter(party=party).order_by("date", "id")


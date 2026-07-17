from django.db import transaction
from decimal import Decimal

from apps.common.exceptions import DomainError
from apps.catalogue.models import ItemCompanyMapping
from apps.catalogue.services import update_rate
from apps.stock.services import post_movement
from apps.parties.services import post_entry
from ..models import Purchase, PurchaseLine
from .numbering import next_number
from .charges import apply_charges, persist_charges


@transaction.atomic
def create_purchase(user, company, fy, party, date, lines, number=None, charges=None):
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    num = next_number(company, fy, "PURCHASE", manual=number)
    purchase = Purchase.objects.create(
        company=company, financial_year=fy, party=party,
        date=date, number=num, created_by=user,
    )
    total = Decimal("0.00")
    for ln in lines:
        mapping = ItemCompanyMapping.objects.select_for_update().get(
            pk=ln["mapping"], company=company
        )
        qty = Decimal(str(ln["qty"]))
        rate = Decimal(str(ln["rate"]))
        amount = qty * rate
        total += amount
        PurchaseLine.objects.create(
            purchase=purchase, item=mapping.item, mapping=mapping,
            qty=qty, rate=rate, amount=amount,
        )
        if rate != mapping.rate:
            update_rate(mapping.id, rate)
        post_movement(mapping.id, date, fy, qty_in=qty,
                      voucher_type="PURCHASE", voucher_id=purchase.id)

    final_total, resolved_charges = apply_charges(total, charges or [])
    if resolved_charges:
        persist_charges("PURCHASE", purchase.id, resolved_charges)

    purchase.total_amount = final_total
    purchase.save(update_fields=["total_amount"])
    post_entry(party, date, fy, "PURCHASE", purchase.id, credit=final_total)
    return purchase

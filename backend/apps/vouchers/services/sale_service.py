from django.db import transaction
from decimal import Decimal

from apps.common.exceptions import DomainError
from apps.catalogue.models import ItemCompanyMapping
from apps.catalogue.services import update_rate
from apps.parties.services import post_entry
from apps.accounts.selectors import default_company, is_multi_mode
from ..models import SaleMaster, SaleLine
from .numbering import next_number
from .segregation import segregate
from .charges import apply_charges, persist_charges


@transaction.atomic
def create_sale(user, company, fy, party, date, lines, number=None,
                segregate_flag=None, charges=None):
    if not fy.is_writable:
        raise DomainError("Financial year is not writable.")
    multi = is_multi_mode(user)
    seg = bool(segregate_flag) if (multi and segregate_flag is not None) else False

    num = next_number(company, fy, "SALE", manual=number)
    master = SaleMaster.objects.create(
        company=company, financial_year=fy, party=party, date=date,
        number=num, segregate=seg, created_by=user,
    )

    seen = set()
    total = Decimal("0.00")
    for ln in lines:
        item_id = ln["item"]
        resolved_company_id = ln.get("company") or (
            company.id if not multi else default_company(user).id
        )
        mapping = ItemCompanyMapping.objects.select_for_update().filter(
            item_id=item_id, company_id=resolved_company_id
        ).select_related("company").first()
        if mapping is None:
            raise DomainError("No item-company mapping for the selected line.")

        key = (item_id, resolved_company_id)
        if key in seen:
            raise DomainError("Duplicate item for the same company in one bill.")
        seen.add(key)

        qty = Decimal(str(ln["qty"]))
        rate = Decimal(str(ln.get("rate", mapping.rate)))
        amount = qty * rate
        total += amount
        SaleLine.objects.create(
            master=master, item_id=item_id, mapping=mapping,
            company_resolved=mapping.company, qty=qty, rate=rate, amount=amount,
        )
        if rate != mapping.rate:
            update_rate(mapping.id, rate)

    # 1. Persist master-level charges (discount / round-off) computed on subtotal.
    final_total, resolved_charges = apply_charges(total, charges or [])
    if resolved_charges:
        persist_charges("SALE", master.id, resolved_charges)

    # 2. Segregate: prorates charges + per-company round-off into derived bills.
    derived = segregate(master)

    # 3. Master total = sum of the legal derived invoices (per-company rounding),
    #    so master == sum(derived) and the ledger posts the real billed figure.
    master_total = sum((d.total_amount for d in derived), Decimal("0.00")) or final_total
    master.total_amount = master_total
    master.save(update_fields=["total_amount"])
    post_entry(party, date, fy, "SALE", master.id, debit=master_total)

    return master


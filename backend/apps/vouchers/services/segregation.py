from django.db import transaction
from decimal import Decimal
from collections import defaultdict

from apps.stock.services import post_movement
from ..models import SaleDerived, SaleLine
from .numbering import next_number
from .charges import prorate_master_charges, persist_charges


@transaction.atomic
def segregate(master):
    lines = list(SaleLine.objects.select_for_update().filter(master=master))
    groups = defaultdict(list)
    for ln in lines:
        groups[ln.company_resolved_id].append(ln)

    # pre-charge subtotal per company (line-value weight for proration)
    groups_value = {
        cid: sum((l.amount for l in grp), Decimal("0.00"))
        for cid, grp in groups.items()
    }
    charge_map = prorate_master_charges(master.id, groups_value)

    derived_map = {}
    for company_id, group in groups.items():
        company = group[0].company_resolved
        line_total = groups_value[company_id]
        charges = charge_map.get(company_id, [])
        charge_sum = sum((c["amount"] for c in charges), Decimal("0.00"))
        derived_total = line_total + charge_sum

        num = next_number(company, master.financial_year, "SALE_DERIVED")
        derived = SaleDerived.objects.create(
            company=company, financial_year=master.financial_year,
            party=master.party, master=master, date=master.date,
            number=num, total_amount=derived_total, created_by=master.created_by,
        )
        if charges:
            persist_charges("SALE_DERIVED", derived.id, charges)

        derived_map[company_id] = derived
        for ln in group:
            ln.derived = derived
            ln.save(update_fields=["derived"])
            post_movement(ln.mapping_id, master.date, master.financial_year,
                          qty_out=ln.qty, voucher_type="SALE", voucher_id=derived.id)
    return list(derived_map.values())

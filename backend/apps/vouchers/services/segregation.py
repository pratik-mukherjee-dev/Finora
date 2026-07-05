from django.db import transaction
from decimal import Decimal
from collections import defaultdict

from apps.stock.services import post_movement
from ..models import SaleDerived, SaleLine
from .numbering import next_number


@transaction.atomic
def segregate(master):
    lines = list(SaleLine.objects.select_for_update().filter(master=master))
    groups = defaultdict(list)
    for ln in lines:
        groups[ln.company_resolved_id].append(ln)

    derived_map = {}
    for company_id, group in groups.items():
        company = group[0].company_resolved
        total = sum((l.amount for l in group), Decimal("0.00"))
        num = next_number(company, master.financial_year, "SALE_DERIVED")
        derived = SaleDerived.objects.create(
            company=company, financial_year=master.financial_year,
            party=master.party, master=master, date=master.date,
            number=num, total_amount=total, created_by=master.created_by,
        )
        derived_map[company_id] = derived
        for ln in group:
            ln.derived = derived
            ln.save(update_fields=["derived"])
            post_movement(ln.mapping_id, master.date, master.financial_year,
                          qty_out=ln.qty, voucher_type="SALE", voucher_id=derived.id)
    return list(derived_map.values())

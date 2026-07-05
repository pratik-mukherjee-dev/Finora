from django.db import transaction

from apps.common.exceptions import DomainError
from ..models import VoucherNumberSeq


@transaction.atomic
def next_number(company, fy, voucher_type, manual=None):
    seq, _ = VoucherNumberSeq.objects.select_for_update().get_or_create(
        company=company, financial_year=fy, voucher_type=voucher_type,
    )
    if manual:
        n = _extract_seq(manual, seq.template)
        if n is not None and n > seq.high_water:
            seq.high_water = n
            seq.save(update_fields=["high_water"])
        return manual
    seq.high_water += 1
    seq.save(update_fields=["high_water"])
    try:
        return seq.template.format(seq=seq.high_water)
    except (KeyError, ValueError):
        raise DomainError("Invalid voucher number template.")


def _extract_seq(value, template):
    import re
    prefix = template.split("{")[0]
    if prefix and value.startswith(prefix):
        tail = value[len(prefix):]
    else:
        tail = value
    m = re.search(r"(\d+)", tail)
    return int(m.group(1)) if m else None

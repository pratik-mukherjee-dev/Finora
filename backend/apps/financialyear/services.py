from django.db import transaction
from django.utils import timezone

from ..common.exceptions import DomainError
from .models import FinancialYear
from .selectors import active_fy, next_fy


@transaction.atomic
def open_first_fy(user, start_date, end_date):
    if active_fy(user):
        raise DomainError("An active financial year already exists.")
    return FinancialYear.objects.create(
        user=user, start_date=start_date, end_date=end_date, is_active=True
    )


@transaction.atomic
def close_year(user, fy, create_next=True, next_end_date=None):
    fy = FinancialYear.objects.select_for_update().get(pk=fy.pk)
    if not fy.is_active or fy.is_closed:
        raise DomainError("Only the active, open financial year can be closed.")

    nxt = next_fy(user, fy)
    if create_next and nxt is None:
        from datetime import timedelta
        start = fy.end_date + timedelta(days=1)
        end = next_end_date or fy.end_date.replace(year=fy.end_date.year + 1)
        nxt = FinancialYear.objects.create(
            user=user, start_date=start, end_date=end, is_active=False
        )

    fy.is_active = False
    fy.is_closed = True
    fy.save(update_fields=["is_active", "is_closed"])

    if nxt:
        nxt.is_active = True
        nxt.is_closed = False
        nxt.save(update_fields=["is_active", "is_closed"])
        from apps.stock.services import carry_forward_stock
        carry_forward_stock(from_fy=fy, to_fy=nxt)

    return nxt

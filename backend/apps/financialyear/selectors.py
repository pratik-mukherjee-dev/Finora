from .models import FinancialYear


def active_fy(user):
    return FinancialYear.objects.filter(user=user, is_active=True, is_closed=False).first()


def next_fy(user, after):
    return (
        FinancialYear.objects.filter(user=user, start_date__gt=after.start_date)
        .order_by("start_date")
        .first()
    )

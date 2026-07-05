from decimal import Decimal
from django.db.models import Sum, Q

from apps.vouchers.models import SaleDerived, Purchase, Received, Payment
from apps.stock.models import StockLedger


def _date_range(qs, date_from, date_to):
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    return qs


def sales_report(user, company=None, party=None, date_from=None, date_to=None,
                 category=None, item=None):
    qs = SaleDerived.objects.filter(company__user=user)
    if company:
        qs = qs.filter(company_id=company)
    if party:
        qs = qs.filter(party_id=party)
    qs = _date_range(qs, date_from, date_to)
    if item or category:
        line_q = Q()
        if item:
            line_q &= Q(lines__item_id=item)
        if category:
            line_q &= Q(lines__mapping__category_id=category)
        qs = qs.filter(line_q).distinct()
    total = qs.aggregate(s=Sum("total_amount"))["s"] or Decimal("0.00")
    return {"count": qs.count(), "total": total, "rows": qs}


def purchase_report(user, company=None, party=None, date_from=None, date_to=None,
                    category=None, item=None):
    qs = Purchase.objects.filter(company__user=user)
    if company:
        qs = qs.filter(company_id=company)
    if party:
        qs = qs.filter(party_id=party)
    qs = _date_range(qs, date_from, date_to)
    if item or category:
        line_q = Q()
        if item:
            line_q &= Q(lines__item_id=item)
        if category:
            line_q &= Q(lines__mapping__category_id=category)
        qs = qs.filter(line_q).distinct()
    total = qs.aggregate(s=Sum("total_amount"))["s"] or Decimal("0.00")
    return {"count": qs.count(), "total": total, "rows": qs}


def stock_report(user, company=None, mapping=None, date_from=None, date_to=None):
    qs = StockLedger.objects.filter(mapping__company__user=user)
    if company:
        qs = qs.filter(mapping__company_id=company)
    if mapping:
        qs = qs.filter(mapping_id=mapping)
    qs = _date_range(qs, date_from, date_to)
    agg = qs.aggregate(i=Sum("qty_in"), o=Sum("qty_out"))
    return {
        "in": agg["i"] or Decimal("0.000"),
        "out": agg["o"] or Decimal("0.000"),
        "rows": qs,
    }


def daily_sheet(user, date, company=None):
    def _sum(model, sign_field="total_amount"):
        qs = model.objects.filter(company__user=user, date=date)
        if company:
            qs = qs.filter(company_id=company)
        return qs.aggregate(s=Sum(sign_field))["s"] or Decimal("0.00")

    sales = _sum(SaleDerived)
    purchases = _sum(Purchase)
    received = _sum(Received, "amount")
    paid = _sum(Payment, "amount")
    return {
        "date": date,
        "sales": sales,
        "purchases": purchases,
        "received": received,
        "paid": paid,
        "net_cash": received - paid,
    }

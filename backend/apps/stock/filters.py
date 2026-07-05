import django_filters as df
from .models import StockLedger


class StockLedgerFilter(df.FilterSet):
    date_from = df.DateFilter(field_name="date", lookup_expr="gte")
    date_to = df.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = StockLedger
        fields = ["mapping", "voucher_type", "financial_year", "date_from", "date_to"]

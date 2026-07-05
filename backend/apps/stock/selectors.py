from decimal import Decimal
from .models import StockLedger


def mapping_balance(mapping):
    last = StockLedger.objects.filter(mapping=mapping).order_by("date", "id").last()
    return last.balance if last else Decimal("0.000")

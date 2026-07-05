from django.db import models
from decimal import Decimal


class StockLedger(models.Model):
    mapping = models.ForeignKey(
        "catalogue.ItemCompanyMapping", on_delete=models.PROTECT, related_name="stock_ledger"
    )
    date = models.DateField(db_index=True)
    financial_year = models.ForeignKey(
        "financialyear.FinancialYear", on_delete=models.PROTECT, related_name="stock_ledger"
    )
    qty_in = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0.000"))
    qty_out = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0.000"))
    balance = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0.000"))
    voucher_type = models.CharField(max_length=20)
    voucher_id = models.PositiveBigIntegerField(null=True, blank=True)
    is_manual = models.BooleanField(default=False)
    is_reversal = models.BooleanField(default=False)
    is_opening = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["mapping_id", "date", "id"]
        indexes = [
            models.Index(fields=["mapping", "date"]),
            models.Index(fields=["voucher_type", "voucher_id"]),
        ]


class StockConversion(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="stock_conversions"
    )
    date = models.DateField(db_index=True)
    financial_year = models.ForeignKey(
        "financialyear.FinancialYear", on_delete=models.PROTECT, related_name="stock_conversions"
    )
    source_mapping = models.ForeignKey(
        "catalogue.ItemCompanyMapping", on_delete=models.PROTECT, related_name="conversions_out"
    )
    target_mapping = models.ForeignKey(
        "catalogue.ItemCompanyMapping", on_delete=models.PROTECT, related_name="conversions_in"
    )
    source_qty = models.DecimalField(max_digits=16, decimal_places=3)
    target_qty = models.DecimalField(max_digits=16, decimal_places=3)
    is_cancelled = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

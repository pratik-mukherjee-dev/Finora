from django.db import models
from django.conf import settings
from decimal import Decimal


class Party(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parties"
    )
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    opening_balance = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal("0.00")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_party_name_per_user")
        ]
        indexes = [models.Index(fields=["user", "name"])]

    def __str__(self):
        return self.name


class PartyLedger(models.Model):
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="ledger")
    date = models.DateField(db_index=True)
    financial_year = models.ForeignKey(
        "financialyear.FinancialYear", on_delete=models.PROTECT, related_name="party_ledger"
    )
    voucher_type = models.CharField(max_length=20)
    voucher_id = models.PositiveBigIntegerField()
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    balance = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    is_reversal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["party_id", "date", "id"]
        indexes = [
            models.Index(fields=["party", "date"]),
            models.Index(fields=["voucher_type", "voucher_id"]),
        ]

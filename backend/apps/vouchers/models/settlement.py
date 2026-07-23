from django.db import models
from decimal import Decimal

from .base import VoucherBase


class Received(VoucherBase):
    party = models.ForeignKey(
        "parties.Party", on_delete=models.PROTECT, related_name="receipts"
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    mode = models.ForeignKey(
        'accounts.SettlementMode',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="receipts",
    )
    transaction_ref = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text='UPI ref, UTR, cheque number, etc.'
    )

    class Meta(VoucherBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["company", "financial_year", "number"],
                name="uniq_received_number",
            )
        ]


class Payment(VoucherBase):
    party = models.ForeignKey(
        "parties.Party", on_delete=models.PROTECT, related_name="payments"
    )
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    mode = models.ForeignKey(
        'accounts.SettlementMode',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="payments",
    )
    transaction_ref = models.CharField(
        max_length=100,
        blank=True, null=True,
        help_text='UPI ref, UTR, cheque number, etc.'
    )

    class Meta(VoucherBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["company", "financial_year", "number"],
                name="uniq_payment_number",
            )
        ]


class Allocation(models.Model):
    settlement_type = models.CharField(max_length=20)   # RECEIVED | PAYMENT
    settlement_id = models.PositiveBigIntegerField()
    bill_type = models.CharField(max_length=20)         # SALE | PURCHASE
    bill_id = models.PositiveBigIntegerField()
    amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    is_reversal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["settlement_type", "settlement_id"]),
            models.Index(fields=["bill_type", "bill_id"]),
        ]

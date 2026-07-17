from django.db import models
from decimal import Decimal
from apps.common.models import SoftCancelModel


class VoucherCharge(SoftCancelModel):
    SALE = 'SALE'
    PURCHASE = 'PURCHASE'
    VOUCHER_TYPE_CHOICES = (
        (SALE, 'Sale'),
        (PURCHASE, 'Purchase'),
    )

    DISCOUNT = "DISCOUNT"
    ROUND_OFF = "ROUND_OFF"
    CGST = "CGST"
    SGST = "SGST"
    CHARGE_TYPE_CHOICES = (
        (DISCOUNT, "Discount"),
        (ROUND_OFF, "Round Off"),
        (CGST, "CGST"),
        (SGST, "SGST"),
    )

    PERCENT = "PERCENT"
    AMOUNT = "AMOUNT"
    MODE_CHOICES = (
        (PERCENT, "Percent"),
        (AMOUNT, "Amount")
    )

    voucher_type = models.CharField(
        max_length=20,
        choices=VOUCHER_TYPE_CHOICES,
    )
    voucher_id = models.PositiveBigIntegerField()

    ledger = models.ForeignKey(
        'ledgers.Ledger',
        on_delete=models.PROTECT,
        related_name='voucher_charges',
    )

    charge_type = models.CharField(
        max_length=20,
        choices=CHARGE_TYPE_CHOICES,
    )

    mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default=PERCENT,
    )

    input_value = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        default=Decimal("0.0000")
    )

    # signed effect on the bill total: discount negative, tax/round-off may be +/-
    amount = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal("0.00")
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["voucher_type", "voucher_id", "sort_order", "id"]
        indexes = [
            models.Index(fields=["voucher_type", "voucher_id"]),
        ]


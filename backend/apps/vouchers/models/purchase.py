from django.db import models

from .base import VoucherBase


class Purchase(VoucherBase):
    party = models.ForeignKey(
        "parties.Party", on_delete=models.PROTECT, related_name="purchases"
    )

    class Meta(VoucherBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["company", "financial_year", "number"],
                name="uniq_purchase_number",
            )
        ]


class PurchaseLine(models.Model):
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(
        "catalogue.Item", on_delete=models.PROTECT, related_name="purchase_lines"
    )
    mapping = models.ForeignKey(
        "catalogue.ItemCompanyMapping", on_delete=models.PROTECT,
        related_name="purchase_lines",
    )
    qty = models.DecimalField(max_digits=16, decimal_places=3)
    rate = models.DecimalField(max_digits=14, decimal_places=2)
    amount = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        indexes = [models.Index(fields=["purchase"])]

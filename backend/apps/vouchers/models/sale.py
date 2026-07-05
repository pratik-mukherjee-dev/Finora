from django.db import models

from .base import VoucherBase


class SaleMaster(VoucherBase):
    party = models.ForeignKey(
        "parties.Party", on_delete=models.PROTECT, related_name="sale_masters"
    )
    segregate = models.BooleanField(default=False)

    class Meta(VoucherBase.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["company", "financial_year", "number"],
                name="uniq_sale_master_number",
            )
        ]


class SaleDerived(VoucherBase):
    party = models.ForeignKey(
        "parties.Party", on_delete=models.PROTECT, related_name="sale_derived"
    )
    master = models.ForeignKey(
        SaleMaster, on_delete=models.PROTECT, related_name="derived"
    )

    class Meta(VoucherBase.Meta):
        pass


class SaleLine(models.Model):
    # belongs to master; company_resolved is the derived target
    master = models.ForeignKey(
        SaleMaster, on_delete=models.CASCADE, related_name="lines"
    )
    derived = models.ForeignKey(
        SaleDerived, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="lines",
    )
    item = models.ForeignKey(
        "catalogue.Item", on_delete=models.PROTECT, related_name="sale_lines"
    )
    mapping = models.ForeignKey(
        "catalogue.ItemCompanyMapping", on_delete=models.PROTECT,
        related_name="sale_lines",
    )
    company_resolved = models.ForeignKey(
        "accounts.Company", on_delete=models.PROTECT, related_name="+"
    )
    qty = models.DecimalField(max_digits=16, decimal_places=3)
    rate = models.DecimalField(max_digits=14, decimal_places=2)
    amount = models.DecimalField(max_digits=16, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["master", "item", "company_resolved"],
                name="uniq_item_company_per_master",
            )
        ]
        indexes = [models.Index(fields=["master", "company_resolved"])]

from django.db import models
from decimal import Decimal

from apps.common.models import AuditModel, SoftCancelModel


class VoucherBase(AuditModel, SoftCancelModel):
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.PROTECT, related_name="%(class)s_set"
    )
    financial_year = models.ForeignKey(
        "financialyear.FinancialYear", on_delete=models.PROTECT, related_name="%(class)s_set"
    )
    number = models.CharField(max_length=40)
    date = models.DateField(db_index=True)
    total_amount = models.DecimalField(
        max_digits=16, decimal_places=2, default=Decimal("0.00")
    )

    class Meta:
        abstract = True
        ordering = ["-date", "-id"]

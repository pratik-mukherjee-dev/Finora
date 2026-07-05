from django.db import models
from ..financialyear.models import FinancialYear


class FYBoundModel(models.Model):
    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.PROTECT,
        related_name="%(class)s_set",
    )

    class Meta:
        abstract = True

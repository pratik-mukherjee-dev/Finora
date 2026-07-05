from django.db import models


class VoucherNumberSeq(models.Model):
    company = models.ForeignKey(
        "accounts.Company", on_delete=models.CASCADE, related_name="number_seqs"
    )
    financial_year = models.ForeignKey(
        "financialyear.FinancialYear", on_delete=models.CASCADE, related_name="number_seqs"
    )
    voucher_type = models.CharField(max_length=20)
    template = models.CharField(max_length=60, default="{seq:04d}")
    high_water = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "financial_year", "voucher_type"],
                name="uniq_seq_per_company_fy_type",
            )
        ]

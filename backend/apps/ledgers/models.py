from django.db import models
from django.conf import settings
from apps.accounts.models import Company
from apps.common.models import AuditModel


class Ledger(AuditModel):
    DISCOUNT = 'DISCOUNT'
    ROUND_OFF = 'ROUND_OFF'
    TAX = 'TAX'
    OTHER = 'OTHER'
    KIND_CHOICES = (
        (DISCOUNT, 'Discount'),
        (ROUND_OFF, 'Round Off'),
        (TAX, 'Tax'),
        (OTHER, 'Other'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ledgers',
    )
    
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='ledgers',
    )

    name = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=OTHER,
    )
    is_system = models.BooleanField(default=False)

    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['kind', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=["user", "company", "name"],
                name="uniq_ledger_name_per_scope",
            )
        ]
        indexes = [models.Index(fields=["user", "kind"])]

    def __str__(self):
        return self.name



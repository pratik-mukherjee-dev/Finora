from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal

from ..accounts.models import Company


class Item(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="items"
    )
    name = models.CharField(max_length=200)
    base_unit = models.CharField(max_length=30, default="pcs")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_item_name_per_user")
        ]
        indexes = [models.Index(fields=["user", "name"])]

    def __str__(self):
        return self.name


class ItemCategory(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="item_categories"
    )
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"], name="uniq_category_name_per_company"
            )
        ]

    def __str__(self):
        return self.name


class ItemCompanyMapping(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="mappings")
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="item_mappings"
    )
    category = models.ForeignKey(
        ItemCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mappings",
    )
    rate = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    stock = models.DecimalField(max_digits=16, decimal_places=3, default=Decimal("0.000"))
    opening_stock = models.DecimalField(
        max_digits=16, decimal_places=3, default=Decimal("0.000")
    )

    # GST placeholders (v2) — nullable, no logic in v1
    hsn_code = models.CharField(max_length=15, null=True, blank=True)
    gst_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    gst_mode = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item", "company"], name="uniq_item_per_company"
            )
        ]
        indexes = [models.Index(fields=["company", "item"])]

    def __str__(self):
        return f"{self.item.name} @ {self.company.name}"

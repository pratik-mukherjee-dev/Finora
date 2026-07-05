from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class FinancialYear(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="financial_years",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False, db_index=True)
    is_closed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_active=True),
                name="uniq_active_fy_per_user",
            ),
            models.CheckConstraint(
                check=models.Q(end_date__gt=models.F("start_date")),
                name="fy_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.start_date}–{self.end_date}"

    def clean(self):
        if self.is_active and self.is_closed:
            raise ValidationError("A closed FY cannot be active.")

    @property
    def is_writable(self):
        return self.is_active and not self.is_closed

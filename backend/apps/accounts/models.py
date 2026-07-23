from django.db import models
from django.contrib.auth.models import AbstractUser
from django.views.decorators.http import condition

from apps.common.models import AuditModel


class User(AbstractUser):
    pass


class Company(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="companies")
    name = models.CharField(max_length=200)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="uniq_default_company_per_user",
            ),
            models.UniqueConstraint(
                fields=["user", "name"], name="uniq_company_name_per_user"
            ),
        ]

    def __str__(self):
        return self.name


class License(models.Model):
    SINGLE = "single"
    MULTI = "multi"
    MODE_CHOICES = [(SINGLE, "Single company"), (MULTI, "Multi company")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="license")
    plan = models.CharField(max_length=50, default="base")
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=SINGLE)
    is_active = models.BooleanField(default=True)
    valid_till = models.DateField(null=True, blank=True)
    max_companies = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(mode__in=["single", "multi"]),
                name="license_mode_valid",
            )
        ]

    @property
    def allows_multi(self):
        return self.mode == self.MULTI and self.is_active


class UserCompanySetting(models.Model):
    SINGLE = "single"
    MULTI = "multi"
    MODE_CHOICES = [(SINGLE, "Single"), (MULTI, "Multi")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="company_setting")
    active_mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=SINGLE)
    default_company = models.ForeignKey(
        Company, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    segregation_enabled = models.BooleanField(default=False)
    is_mode_locked = models.BooleanField(default=True)


class SettlementMode(AuditModel):
    """
        User-scoped payment/received method catalogue.
        Users create descriptive names like "PhonePe - SBI", "Paytm", "HDFC Cheque".
        category + bank_type provide structural metadata for UI grouping and validation.
        System rows can't be deleted (guarded in the service/view).
    """
    CATEGORY_CHOICES = (
        ('CASH', 'Cash'),
        ('BANK', 'Bank'),
    )
    BANK_TYPE_CHOICES = (
        ('UPI', 'UPI'),
        ('TRANSFER', 'Transfer'),
        ('CHEQUE', 'Cheque'),
        ('OTHER', 'Other'),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="settlement_modes",
    )

    name = models.CharField(max_length=60)
    category = models.CharField(
        max_length=10,
        choices=CATEGORY_CHOICES,
        default='CASH',
    )
    bank_type = models.CharField(
        max_length=10,
        choices=BANK_TYPE_CHOICES,
        blank=True, null=True,
        help_text='Only relevant when category is bank.'
    )
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order =models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_settlement_mode_per_user'
            )
        ]

    def needs_reference(self):
        return self.category == 'BANK'

    def __str__(self):
        return self.name


class CompanyBankDetail(AuditModel):
    """
        Default bank details for a company. Printed on sale invoices.
        One company can have multiple bank accounts; one is marked is_default.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="bank_details",
    )
    bank_name = models.CharField(max_length=120)
    account_number = models.CharField(max_length=40)
    ifsc_code = models.CharField(max_length=20, blank=True, default="")
    branch = models.CharField(max_length=120, blank=True, default="")
    account_holder = models.CharField(max_length=200, blank=True, default="")
    upi_id = models.CharField(max_length=100, blank=True, default="")
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_default', 'bank_name']
        constraints = [
            models.UniqueConstraint(
                fields=['company'],
                condition=models.Q(is_default=True),
                name='unique_default_bank_per_company'
            )
        ]

    def __str__(self):
        return f"{self.bank_name} - ({self.account_number})"


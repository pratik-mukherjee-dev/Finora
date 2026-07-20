from django.db import models
from django.contrib.auth.models import AbstractUser
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
        User scoped payment/received method catalogue (Cash, UPI, etc...)
        Seeded with system defaults at registration time; user may add more from settings
        System rows can't be deleted (guarded in the service/view)
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="settlement_modes",
    )

    name = models.CharField(max_length=60)
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

    def __str__(self):
        return self.name



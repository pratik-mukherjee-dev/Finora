from django.db import models
from django.conf import settings


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class NonCancelledManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_cancelled=False)


class SoftCancelModel(models.Model):
    is_cancelled = models.BooleanField(default=False, db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    objects = NonCancelledManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_cancel(self, user=None):
        from django.utils import timezone
        self.is_cancelled = True
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.save(update_fields=["is_cancelled", "cancelled_at", "cancelled_by"])

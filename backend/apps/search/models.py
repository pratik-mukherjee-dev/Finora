from django.db import models
from django.conf import settings


class UsageCounter(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_counters"
    )
    entity_type = models.CharField(max_length=20)   # ITEM | PARTY
    entity_id = models.PositiveBigIntegerField()
    count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "entity_type", "entity_id"],
                name="uniq_usage_per_user_entity",
            )
        ]
        indexes = [models.Index(fields=["user", "entity_type"])]

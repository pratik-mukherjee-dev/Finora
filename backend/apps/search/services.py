from django.db import transaction
from django.db.models import F

from .models import UsageCounter


@transaction.atomic
def record_usage(user, entity_type, entity_id):
    obj, created = UsageCounter.objects.get_or_create(
        user=user, entity_type=entity_type, entity_id=entity_id,
        defaults={"count": 1},
    )
    if not created:
        UsageCounter.objects.filter(pk=obj.pk).update(count=F("count") + 1)
    return obj

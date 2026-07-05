from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Value, IntegerField, Case, When, Q
from django.db.models.functions import Coalesce
from django.db.models import Subquery, OuterRef

from apps.catalogue.models import Item
from apps.parties.models import Party
from .models import UsageCounter


def _rank(qs, user, entity_type, q):
    usage = UsageCounter.objects.filter(
        user=user, entity_type=entity_type, entity_id=OuterRef("pk")
    ).values("count")[:1]
    return (
        qs.annotate(
            sim=TrigramSimilarity("name", q),
            freq=Coalesce(Subquery(usage, output_field=IntegerField()), Value(0)),
            prefix=Case(
                When(name__istartswith=q, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )
        .filter(Q(sim__gt=0.1) | Q(name__icontains=q))
        .order_by("-freq", "-prefix", "-sim", "name")
    )


def suggest_items(user, q, limit=10):
    qs = Item.objects.filter(user=user)
    return _rank(qs, user, "ITEM", q)[:limit]


def suggest_parties(user, q, limit=10):
    qs = Party.objects.filter(user=user)
    return _rank(qs, user, "PARTY", q)[:limit]

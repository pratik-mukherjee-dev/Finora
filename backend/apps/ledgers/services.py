from django.db import transaction
from .models import Ledger


# Default ledgers seeded per user (shared across companies).
DEFAULT_LEDGERS = (
    ('Discount', Ledger.DISCOUNT),
    ("Round Off", Ledger.ROUND_OFF),
    ("CGST", Ledger.TAX),
    ("SGST", Ledger.TAX),
)


@transaction.atomic
def seed_default_ledgers(user):
    """Idempotent: create the standard system ledgers if missing (company=null)."""
    created = []
    for name, kind in DEFAULT_LEDGERS:
        obj, was_created = Ledger.objects.get_or_create(
            user=user, company=None, name=name,
            defaults={"kind": kind, "is_system": True, "created_by": user},
        )
        if was_created:
            created.append(obj)
    return created


@transaction.atomic
def create_ledger(user, name, kind, company=None, gst_rate=None, created_by=None):
    return Ledger.objects.create(
        user=user, company=company, name=name.strip(),
        kind=kind, gst_rate=gst_rate, created_by=created_by or user,
    )
